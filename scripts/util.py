#!/usr/bin/env python

from __future__ import print_function
import os
import sys
import subprocess
import io
import re
import collections
import logging
import json

import socket
import platform

def run(cmd,logger=None,stop_on_error=True,dry_run=False,folder='.'):
    logger = logger or logging.getLogger(__name__)
    logger.info("running-->"+' '.join(cmd)+"<-")
    if not dry_run :
        myprocess = subprocess.Popen(cmd, cwd=folder,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        stdout,stderr = myprocess.communicate()
        myprocess.wait()
        ret = myprocess.returncode
        if stop_on_error and ret:
            #print("ERROR:",ret,"Exiting")
            logger.error("ERROR CODE : " + str(ret) + '\n'+stderr+'\nExit...\n')
            sys.exit()
        return (ret,stdout,stderr)

    else:
        logger.info("DRY RUN... nothing done")
        return (0, '','')


def source(sourcefile):
    source = 'source '+ sourcefile
    dump = sys.executable + ' -c "import os, json;print json.dumps(dict(os.environ))"'
    pipe = subprocess.Popen(['/bin/bash', '-c', '%s && %s' %(source,dump)], stdout=subprocess.PIPE)
    env = json.loads(pipe.stdout.read())
    os.environ = env

class baseintrospect:
    def __init__(self):
        self.sysintro=dict()
        self.sysintro['pyver']=platform.python_version()
        self.sysintro['pyinterp']=sys.executable
        self.sysintro['sysplatform']=platform.platform()
        self.sysintro['commandline']=' '.join(sys.argv)
        self.sysintro['workdir']=os.path.abspath('.')
        self.sysintro['hostname']=socket.getfqdn()

class commandintrospect(baseintrospect):
    def __init__(self,commands=[]):
	baseintrospect.__init__(self)
        self.commands=dict()
        for c in commands:
            self.test(c)

    def test(self,cmd,key=None):
        (ret,o,e)=run(cmd.split())
        if not e :
            if not key : key=cmd
            self.commands[key]=o.strip()

class myintrospect(commandintrospect):
    def __init__(self,tags={}):

        commandintrospect.__init__(self,['git --version'])

        self.test('git config --get remote.origin.url',key='giturl')
        self.tags=tags

    def platform_tag(self):
        hostname=self.sysintro['hostname']
        for k in self.tags:
            m=re.search(k,hostname)
            if m : return self.tags[k]
        return(None)


    #     (out,err)=run('svn info '+self.sysintro['workdir'])
    #     for (cmd,match) in [("svnurl","URL: "),("svnauthor","Last Changed Author: ")]:
    #         for line in out.splitlines():
	 #        if match in line:
		#     self.commands[cmd] = line[len(match):]
		#     break
    #
    # def reproduce_string(self,comment=''):
    #     out = comment+"module load ba\n"
    #     try:
    #         revision=int(self.commands['svnrevision'])
    #     except :
    #         print "WARNING svn not clean"
    #         c=re.compile('(^[0-9]*)')
    #         m=c.match(self.commands['svnrevision'])
    #         revision=m.groups()[0]
    #     out +=comment+"svn co "+self.commands['svnurl']+'@'+str(revision)+" my_common_source\n"
    #     out +=comment+"cd my_common_source\n"
    #     out +=comment+self.sysintro['pyinterp']+' '+self.sysintro['commandline']+'\n'
    #     return out


class git_repo:
    def __init__(self, folder, logger=None,stop_on_error=True,dry_run=False):
        self.folder = os.path.abspath(folder)
        self.logger = logger or logging.getLogger(__name__)
        self.stop_on_error=stop_on_error
        self.dry_run=dry_run
        #print("debug level-->",self.debug)

    def run(self,cmd):
        (ret,out,err)=run(cmd,logger=self.logger,dry_run=self.dry_run,stop_on_error=self.stop_on_error,folder=self.folder)
        return (ret,out)

    def init(self):
        if not os.path.exists(self.folder):
            os.makedirs(self.folder)
        cmd = ['git', 'rev-parse', '--show-toplevel']
        (ret,output) = self.run(cmd)
        git_root = os.path.abspath(output.strip())

        #print("in path ",self.folder," git rev_parse ret: ",ret, ' git top:', git_root)
        self.logger.info("in path "+self.folder+" git rev_parse ret: "+str(ret)+ ' git top:'+ git_root)
        if 0 != ret or git_root != self.folder:
            cmd = ['git', 'init']
            (ret,output) = self.run(cmd)
            self.logger.info("git init in >>" + self.folder + "<< >>" + git_root + "<< ret= "+ str(ret))
            #print("git init in ",">>" + self.folder + "<<",">>" + git_root + "<< ret= ",ret)

    def get_remotes(self):
        cmd = ['git', 'remote']
        (ret,output) = self.run(cmd)
        remotes = list()
        for line in io.StringIO(output.decode()):
            r=line.strip()
            remotes.append(r)
            #print("-->" + r + "<--")
        return remotes

    def add_remote(self, url, name='origin', fetch_branches=[]):
        remotes=self.get_remotes()
        #if self.debug : print("remotes-->",remotes,"<<-")
        self.logger.debug("remotes-->"+str(remotes)+"<<-")
        if name not in self.get_remotes():
            cmd = ['git', 'remote', 'add']
            for branch in fetch_branches:
                cmd.append('-t')
                cmd.append(branch)
            cmd += [name, url]

            (ret,output) = self.run(cmd)


    def fetch(self, name='origin', prefix='',  branches=[]):
        cmd = [ 'git', 'fetch', name ]

        if isinstance(branches,list):
            for branch in branches:
 #               cmd.append(branch)
                cmd.append( branch + ':' + prefix.format(name=name) + branch)
        elif isinstance(branches,dict):
            for branch in branches:
                cmd.append( branch + ':' + prefix.format(name=name) + branches[branch])
        else:
            self.logger.error('Invalid branches type: either list or dict')

            return

        (ret,output) = self.run(cmd)

    def checkout(self, branch, newbranch=None):
        cmd = [ 'git', 'checkout', branch ]
        if newbranch: cmd.extend(['-b', newbranch])
        (ret,output) = self.run(cmd)

    def sync_upstream(self, upstream='upstream', master='develop', options=['--ff-only']):
        cmd = [ 'git', 'pull'] + options  + [upstream, master]
        (ret,output) = self.run(cmd)
        if ret : self.logger.error("sync_upstream failed")

    def merge(self, branch, comment='merged branch '):
        if not comment : comment = 'merged branch ' + branch
        self.logger.info("merging-->" + branch + '<<-')
        cmd = [ 'git', 'merge', '-m', '"' + comment  + '"', branch]
        (ret,output) = self.run(cmd)
        if ret : self.logger.error("merge " + branch + "failed")

    def get_local_branches(self):
        cmd = [ 'git', 'branch']
        (ret,output) = self.run(cmd)
        if ret :
            self.logger.error("git branch failed")
            return []
        branches = list()
        for line in io.StringIO(output.decode()):
            if line[0]=='*':
                branches.insert(0,line[2:].strip())
            else:
                branches.append(line[2:].strip())
        self.logger.debug("branches-->"+str(branches)+"<<-")
        return branches

# ------ List the branches on the origin
# And select only those that match our branch regexp
def get_branches(url, branch_pattern='.*?\s+refs/heads/(.*?)\s+', branch_format_string='{branch}', branch_selection=[]):
    cmd = ['git', 'ls-remote', url]
    output = subprocess.Popen(cmd, stdout=subprocess.PIPE).communicate()[0]

    headRE = re.compile(branch_pattern)

    remote_branches = list()
    for line in io.StringIO(output.decode()):
        match = headRE.match(line)

        if match:
             branch = match.group(1)
            # excludeRE = re.compile(branch_exclude_pattern.format(branch=branch))
            # include=True
            # for line in io.StringIO(output.decode()):
            #     if excludeRE.match(line) :
            #         include= False
            #         print("excluded branch ",branch," line :",line)
            #         break

            # if include : remote_branches.append(branch)
             remote_branches.append(branch)
    remote_branches.sort()

    #  print('#########-->' + url)
    #  for b in remote_branches:
    #    print("       -->",b)
    # ------ Construct the regular expression used to evaluate branches
    branchRE = dict()
    for p in branch_selection:
        # branchRE.append('(' + branch + ')')
        branchRE[p] = re.compile('^(' + p + ')$')
    # branchRE = re.compile('^(' + '|'.join(branchRE) + r')$')

    # ------- Figure out which of those branches we want
    fetch_branches = list()
    checkout_branch = None
    to_match = remote_branches
    for p in branch_selection:
        unmatched = []
        for branch in to_match:
            match2 = branchRE[p].match(branch)
            if match2:
                br_name = branch_format_string.format(branch=branch)
                #        if match2.group(2) and checkout_branch is None:
                #          checkout_branch = br_name
                fetch_branches.append(br_name)
            else:
                unmatched.append(branch)
        to_match = unmatched



    #  print("checkout-->",checkout_branch)
    for b in fetch_branches:
        logging.getLogger(__name__).info('{0} fetch-->'.format(url), b)

    return fetch_branches

def trasf_match(in_list,in_match='(.*)',out_format='{name}'):
    out=collections.OrderedDict()
    in_RE = re.compile(in_match)
    for entry in in_list:
        match = in_RE.match(entry)
        if match:
            if 0 < len(match.groups()):
                name = match.group(1)
                out[entry] = out_format.format(name=name)
    return(out)
