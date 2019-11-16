class Site:
    def __init__(self, name, remote, env, default_treeish, cur_rev, cur_path):
        self.name = name
        self.remote = remote
        self.env = env
        self.default_treeish = default_treeish
        self.cur_rev = cur_rev
        self.cur_path = cur_path
