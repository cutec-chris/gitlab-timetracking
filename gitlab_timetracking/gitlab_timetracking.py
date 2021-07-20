#!/usr/bin/env python
import gitlab,argparse,os,pathlib,json,sys,logging,cmd,time,datetime
try: import pygit2
except: pass
from timesheet_gitlab.timesheet_gitlab import GitLabTimeSheets
DEFAULT_URL = 'https://GitLab.com/'
class GitLabTimeTracking():
    def interactive(self):
        TimeTrackingShell(self).cmdloop()
    def start(self,cmdline):
        if  'project' in self.config\
        and 'task' in self.config\
        and 'started' in self.config:
            self.stop()
        if not self.project:
            logging.error('No Project selected!')
            return False
        self.task = self.project.issues.get(cmdline)
        if not self.task:
            logging.error('No Issue selected!')
            return False
        self.config['task'] = str(self.task.iid)
        self.config['started'] = time.time()
        self._save()
        logging.info('task "%s" started' % self.task.title)
    def stop(self,cmdline=''):
        if  'project' in self.config\
        and 'task' in self.config\
        and 'started' in self.config:
            atime = time.time()-self.config['started']
            atime=atime/60/60
            self.project = self.gl.projects.get(self.config['project'])
            self.task = self.project.issues.get(self.config['task'])
            ftime = '{0:0.0f}h{1:0.0f}m'.format(*divmod(atime * 60, 60))
            try:
                self.task.add_spent_time(ftime)
                del self.config['task']
                del self.config['started']
                self._save()
                logging.info('spend %s on task %s' % (ftime,self.task.title))
            except BaseException as e:
                logging.error(str(e))
    def list(self,cmd):
        self.project = self.gl.projects.get(self.config['project'])
        issues = self.project.issues.list(state='opened')
        for issue in issues:
            print('#%d %s' % (issue.iid,issue.title))
    def abort(self,cmd):
        del self.config['task']
        del self.config['started']
        self._save()
        logging.info('no task started')
    def daily(self,cmd):
        date_events = self.ts._date_events(datetime.datetime.today())
        if date_events:
            timeslots = self.ts._bin_events(date_events)        
        for slot in timeslots:
            print('%s-%s %s' % (str(slot.start),str(slot.finish),str(slot.activities)))
    def status(self):
        if  'project' in self.config\
        and 'task' in self.config\
        and 'started' in self.config:
            atime = time.time()-self.config['started']
            atime=atime/60/60
            self.project = self.gl.projects.get(self.config['project'])
            self.task = self.project.issues.get(self.config['task'])
            ftime = '{0:0.0f}h{1:0.0f}m'.format(*divmod(atime * 60, 60))
            logging.info('%s on task %s' % (ftime,self.task.title))
        else:
            logging.info('no task started')
    def setproject(self,cmdline):
        self.project = None
        try:
            aproject = self.gl.projects.get(cmdline)
            self.project = aproject
        except BaseException as e:
            logging.debug(str(e))
            prepos = self.gl.projects.list(web_url=cmdline)
            for arepo in prepos:
                logging.debug('checking '+arepo.web_url)
                if arepo.web_url == cmdline:
                    self.project = arepo
                    break
        if self.project:
            self.config['project'] = str(self.project.id)
            logging.info('project changed to:'+str(self.project.name))
        else:
            logging.error('project not found')
    def _find_project(self):
        self.project = None
        if self.remote:
            asearch = self.remote.url
            if '.git' in asearch:
                while asearch.find('/')>-1:
                    asearch = asearch[asearch.find('/')+1:]
                asearch = asearch.replace('.git','')
            prepos = self.gl.projects.list(search=asearch)
            logging.debug('repo search: '+str(len(prepos)))
            for arepo in prepos:
                logging.debug('checking '+arepo.name)
                if arepo.ssh_url_to_repo == self.remote.url\
                or arepo.http_url_to_repo == self.remote.url:
                    if 'started' in self.config:
                        logging.info('aborting set project, runing task on other project, found project:')
                        logging.info('project '+str(arepo.id))
                    else:
                        self.project = arepo
                        self.setproject(arepo.id)
                    break
        if 'project' in self.config:
            self.setproject(self.config['project'])
    def _check_repo(self):
        try:
            repo = pygit2.Repository(str(pathlib.Path('.')))
            self.branch = repo.head.shorthand
            self.remote = None
            logging.debug('we are on branch:'+self.branch)
            glurl = self.args.url.lower()
            if '://' in glurl:
                glurl = glurl[glurl.find('://')+3:]
            for r in repo.remotes:
                logging.debug('checking remote:%s (%s)' % (r.name,r.url)) 
                if glurl in r.url.lower():
                    self.remote = r
                    logging.debug('remote::%s (%s)' % (r.name,r.url))
        except BaseException as e:
            self.branch = None
            self.remote = None
            logging.info(str(e))
    def __init__(self):
        self.args = None
        self.gl = None
        self.user = None
        self.config_path = pathlib.Path.home() / '.gitlab_timetracking.json'
        try:
            with open(self.config_path,'r+') as config_file:
                self.config = json.load(config_file)
        except:
            self.config = {}
    def _save(self):
        with open(self.config_path,'w') as config_file:
            json.dump(self.config,config_file)
    def _connect(self):
        """ connects to gitlab server & gets the user that will be analyzed """
        token = self.args.private_token
        if self.args.url == DEFAULT_URL:
            if 'URL' in self.config:
                self.args.url = self.config['URL']
        self.config['URL'] = self.args.url
        if token is None:
            try:
                token = os.environ['PRIVATE_TOKEN']
            except KeyError:
                if 'PRIVATE_TOKEN' in self.config:
                    token = self.config['PRIVATE_TOKEN']
                else:
                    self.config['PRIVATE_TOKEN'] = input("Enter your private token from "+self.args.url+":")
                    token = self.config['PRIVATE_TOKEN']
                    self.config['URL'] = self.args.url
                if token is None:
                    sys.exit(1)
        self.gl = gitlab.Gitlab(self.args.url, private_token=token)
        self.gl.auth()
        current_user = self.gl.user
        my_id = current_user.id
        self.user = self.gl.users.get(my_id)
        logging.debug(f'current_user={self.user.name} id={my_id}')
        self._save()
        self.ts = GitLabTimeSheets()
        self.ts.gl = self.gl
        self.ts.user = self.user
        self.ts.args = self.args
        self.ts.args.filter = ''
        self.ts.args.details = ''
    @staticmethod
    def _setup_command_line_options():
        parser = argparse.ArgumentParser(description=__doc__,
                                         formatter_class=argparse.RawTextHelpFormatter)
        p_add = parser.add_argument
        p_add('-p', '--private_token', metavar='TOKEN',
              help='private token to connect to the GitLab Server. This must\n'
                   'be specified unless the token is supplied using the shell\n'
                   'variable PRIVATE_TOKEN.'
                   ' The token must have read_api access.')
        p_add('-u', '--url', default=DEFAULT_URL,
              help=f'the url of the GitLab server, defaults to {DEFAULT_URL}')
        p_add('--debug', action="store_true",
              help='turn on debug message logging output\n'
                   '(only useful for the program developers).')
        p_add('--start', 
              help='Starts timetracking on an task\n'
                   'specify task with gitlabs #x task number')
        p_add('--stop', 
              help='Stops timetracking on actual task\n')
        return parser
    def _parse_command_line_args(self, parser):
        self.args = parser.parse_args()
    def _deal_with_command_line_args(self):
        parser = self._setup_command_line_options()
        self._parse_command_line_args(parser)
    def run(self):
        self._deal_with_command_line_args()
        if self.args.debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        self._connect()
        self._check_repo()
        self._find_project()
        self.status()
        if self.args.start\
        or self.args.stop:
            pass
        else:
            self.interactive()
    def __del__(self):
        #self.stop()
        pass
class TimeTrackingShell(cmd.Cmd):
    intro = 'Welcome to timetracking. Type help or ? to list commands.\n'
    prompt = '(timetracking) '
    file = None
    def __init__(self, TimeTracking, completekey='tab', stdin=sys.stdin, stdout=sys.stdout) -> None:
        super().__init__(completekey=completekey, stdin=stdin, stdout=stdout)
        self.TimeTracking = TimeTracking
    def do_start(self, arg):
        'Start timetracking on specified Task (Gitlab #id)'
        self.TimeTracking.start(arg)
    def do_stop(self, arg):
        'Start timetracking on specified Task (Gitlab #id)'
        self.TimeTracking.stop(arg)
    def do_project(self, arg):
        'Select an Project with Gitlab URL'
        self.TimeTracking.setproject(arg)
    def do_status(self, arg):
        'Shows status if an task is running'
        self.TimeTracking.status()
    def do_daily(self, arg):
        'Shows daily list of times'
        self.TimeTracking.daily(arg)
    def do_abort(self, arg):
        'Aborts the current running task'
        self.TimeTracking.abort(arg)
    def do_list(self, arg):
        'List open tasks in the current project'
        self.TimeTracking.list(arg)
    def do_quit(self, arg):
        'Exit timetracking'
        sys.exit()
if __name__ == "__main__":
    try:
        GitLabTimeTracking().run()
    except KeyboardInterrupt:
        pass