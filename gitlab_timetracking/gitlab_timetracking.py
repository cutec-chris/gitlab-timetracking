import timesheet_gitlab,gitlab,argparse,os,pathlib,json,sys,logging

DEFAULT_URL = 'https://GitLab.com/'
class GitLabTimeTracking():
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
        p_add('START', nargs='?', default='today',
              help='start date for timesheet as DD-MM-YY.\n'
                   'For instance 20-01-21 for 20 Jan 2021.\n'
                   'If the year or month is left out then current year/month'
                   ' will be used.\n'
                   'If not specified at all the timesheet for today will be'
                   ' produced')
        p_add('FINISH', nargs='?',
              help='finish date for timesheet as DD-MM-YY.\n'
                   'If not specified the timesheet for START day will'
                   ' be produced.')
        p_add('-p', '--private_token', metavar='TOKEN',
              help='private token to connect to the GitLab Server. This must\n'
                   'be specified unless the token is supplied using the shell\n'
                   'variable PRIVATE_TOKEN.'
                   ' The token must have read_api access.')
        p_add('-u', '--url', default=DEFAULT_URL,
              help=f'the url of the GitLab server, defaults to {DEFAULT_URL}')
        p_add('-f', '--filter',
              help='only include projects whose name includes FILTER')
        p_add('-s', '--summary', action='store_true',
              help='do not print daily timesheets. Only the initial summary.')
        p_add('-d', '--details', action='store_true',
              help='For each daily timesheet add a detailed list of each '
                   'individual activities. ')
        p_add('--debug', action='store_true',
              help='turn on debug message logging output\n'
                   '(only useful for the program developers).')
        return parser
    def _parse_command_line_args(self, parser):
        self.args = parser.parse_args()
    def _deal_with_command_line_args(self):
        parser = self._setup_command_line_options()
        self._parse_command_line_args(parser)
    def run(self):
        self._deal_with_command_line_args()
        self._connect()
if __name__ == "__main__":
    GitLabTimeTracking().run()