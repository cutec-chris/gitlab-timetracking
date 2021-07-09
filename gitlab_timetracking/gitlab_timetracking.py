#!/usr/bin/env python
import timesheet_gitlab,gitlab,argparse,os,pathlib,json,sys,logging,pygit2,cmd,time,datetime
DEFAULT_URL = 'https://GitLab.com/'
class GitLabTimeTracking():
    def interactive(self):
        TimeTrackingShell(self).cmdloop()
    def start(self,cmdline):
        if not self.project:
            logging.error('No Project selected!')
            return False
        self.task = self.project.issues.get(cmdline)
        if not self.task:
            logging.error('No Issue selected!')
            return False
        self.config['task'] = str(self.task.iid)
        self.config['started'] = time.time()
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
            self.task.add_spent_time(ftime)
            logging.info('spend %s on task %s' % (ftime,self.task.title))
    def setproject(self,cmdline):
        self.project = None
        try:
            aproject = self.gl.projects.get(cmdline)
            self.project = aproject
        except:
            prepos = self.gl.projects.list(web_url=cmdline)
            for arepo in prepos:
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
            prepos = self.gl.projects.list(ssh_url_to_repo=self.remote.url)
            for arepo in prepos:
                if arepo.ssh_url_to_repo == self.remote.url\
                or arepo.http_url_to_repo == self.remote.url:
                    self.project = arepo
                    self.setproject(arepo.id)
                    break
    def _check_repo(self):
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
    def _connect(self):
        """ connects to gitlab server & gets the user that will be analyzed """
        token = self.args.private_token
        if self.args.url == DEFAULT_URL:
            if 'URL' in self.config:
                self.args.url = self.config['URL']
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
                with open(self.config_path,'w') as config_file:
                    json.dump(self.config,config_file)
                if token is None:
                    sys.exit(1)
        self.gl = gitlab.Gitlab(self.args.url, private_token=token)
        self.gl.auth()
        current_user = self.gl.user
        my_id = current_user.id
        self.user = self.gl.users.get(my_id)
        logging.debug(f'current_user={self.user.name} id={my_id}')
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
        if self.args.start\
        or self.args.stop:
            pass
        else:
            self.interactive()
    def __del__(self):
        self.stop()
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
    def do_quit(self, arg):
        'Exit timetracking'
        sys.exit()
if __name__ == "__main__":
    try:
        GitLabTimeTracking().run()
    except KeyboardInterrupt:
        pass