class Site:
    def __init__(self, name, remote, env, default_treeish):
        self.name = name
        self.remote = remote
        self.env = env
        self.default_treeish = default_treeish