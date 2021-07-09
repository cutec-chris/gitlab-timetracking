import timesheet_gitlab,gitlab,argparse,os,pathlib,json,sys,logging,pygit2

DEFAULT_URL = 'https://GitLab.com/'
class GitLabTimeTracking():
    def start(self,cmdline):
        pass
    def stop(self,cmdline):
        pass
    def _find_project(self):
        if self.remoteurl:
            prepos = self.gl.projects.list(ssh_url_to_repo=self.remoteurl)
            for arepo in prepos:
                if arepo.ssh_url_to_repo == self.remoteurl\
                or arepo.http_url_to_repo == self.remoteurl:
                    self.project = arepo
                    logging.debug('project:'+self.project)
                    break
    def _check_repo(self):
        repo = pygit2.Repository(str(pathlib.Path('.')))
        self.branch = repo.head.shorthand
        self.remoteurl = None
        logging.debug('we are on branch:'+self.branch)
        for r in repo.remotes:
            logging.debug('checking remote:%s (%s)' % (r.name,r.url)) 
            if r.url.lower().startswith(self.args.url.lower()):
                self.remoteurl = r
                logging.debug('remote url:'+self.remoteurl)
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
        self._connect()
        self._check_repo()
        self._find_project()
if __name__ == "__main__":
    GitLabTimeTracking().run()