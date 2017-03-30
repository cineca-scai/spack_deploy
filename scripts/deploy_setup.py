#!/usr/bin/env python


from __future__ import print_function
import pprint, StringIO

import os
import sys
import subprocess
import io
import re
import argparse
import logging
import glob

import util
import mytemplate


parser = argparse.ArgumentParser(description="""
  Clone origin repository, opionally update the develop branch, integrate a list of PR and branches into a new branch
  usage examples: 
   python {scriptname} --prlist 579 984 943 946 1042 797 --branches clean/develop 'pr/(.*)'
   python {scriptname} --debug=1 --dest=../deploy/spack2 --prlist   797 -branches clean/develop 'pr/fix.*' 'pr/.*' 'wip/.*'
""".format(scriptname=sys.argv[0]), formatter_class=argparse.RawTextHelpFormatter)

parser.add_argument('-d', '--debug', action='store',
                    help='debug level: warning,error,debug',
                    default='info')
parser.add_argument('--origin', action='store',
                    help='URL of the origin git repo being cloned.',
                    default='https://github.com/RemoteConnectionManager/spack.git')
parser.add_argument('--logfile', action='store',
                    help='logfile to log into.',
                    default= os.path.splitext(sys.argv[0])[0]+'.log')
parser.add_argument('--upstream', action='store',
                    help='URL of the upstream git repo.', default='https://github.com/LLNL/spack.git')

parser.add_argument('--branches', nargs='*', default=['develop','clean/develop'],
                    help='Regular expressions of origin branches to fetch.  The first one specified will be checked out.')

parser.add_argument('--master', action='store', default='develop',
                    help='name of the branch that will be created.')

parser.add_argument('--upstream_master', action='store', default='develop',
                    help='upstream branch to sync with.')

parser.add_argument('--dry_run', action='store_true', default=False,
                    help='do not perform any action')

parser.add_argument('--integration', action='store_true', default=False,
                    help='do upstream integration')

parser.add_argument('--update', action='store_true', default=False,
                    help='update existing checkout')

parser.add_argument('--pull_flags', nargs='*', action='store', default=['ff-only'],
                    help='flags to use when pull')

parser.add_argument('--prlist', nargs='*', default=[],
                    help='Regular expressions of upstream pr to fetch and merge.')

parser.add_argument('--cache', action='store', default='cache',
                    help='folder where cache is')

parser.add_argument('--install', action='store', default='', 
                    help='folder where install packages')

parser.add_argument('--config', action='store', default='',
                    help='folder containing config information')

parser.add_argument('--clearconfig', action='store_true', default=False,
                    help='clear existing c')


#print("argparse.SUPPRESS-->"+argparse.SUPPRESS+"<---------------")
parser.add_argument('--dest', default=argparse.SUPPRESS,
                    help="Directory to clone into.  If ends in slash, place into that directory; otherwise, \
place into subdirectory named after the URL")
#parser.add_argument('--dest',
#                    help="Directory to clone into.  If ends in slash, place into that directory; otherwise, \
#place into subdirectory named after the URL")

args = parser.parse_args()

#print("-----args-------->", args)
#print("this script-->"+__file__+"<--")
root_dir=os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
#print("root_dir-->"+root_dir+"<--")

# ------ Determine destination directory
destRE = re.compile('.*/(.*?).git')
repo_name = destRE.match(args.origin).group(1)

if 'dest' in args:
    dest = args.dest
    if dest[0] != '/':
        dest = os.path.join(root_dir,dest)
    if dest[-1] == '/':
        dest = os.path.join(dest[:-1], repo_name)

else:
    dest = os.path.join(root_dir,'deploy', repo_name)

print("destination folder-->"+dest+"<--")

logdir=os.path.dirname(args.logfile)
if not os.path.exists( args.logfile ): logdir=dest
logdir=os.path.abspath(logdir)

LEVELS = {'debug': logging.DEBUG,
          'info': logging.INFO,
          'warning': logging.WARNING,
          'error': logging.ERROR,
          'critical': logging.CRITICAL}
loglevel=LEVELS.get(args.debug, logging.INFO)
LONGFORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() %(asctime)s] %(message)s"
SHORTFORMAT = "%(message)s"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
actual_logfile=os.path.join(os.path.dirname(logdir),os.path.basename(logdir)+'_'+os.path.basename(args.logfile))
print("logfile in "+actual_logfile)

fh = logging.FileHandler(os.path.join(actual_logfile))
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(loglevel)

# create formatter and add it to the handlers
long_formatter = logging.Formatter("[%(filename)s:%(lineno)s - %(funcName)20s() %(asctime)s] %(message)s")
short_formatter = logging.Formatter("%(message)s")
ch.setFormatter(short_formatter)
fh.setFormatter(long_formatter)

# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)

#logging.basicConfig(filename=os.path.join(logdir,os.path.basename(args.logfile)))

#logging.basicConfig(level=loglevel)




s = StringIO.StringIO()
pprint.pprint(args, s)

logger.info("lanciato con---->"+s.getvalue())
logger.info("root_dir-->"+root_dir+"<--")




dev_git = util.git_repo(dest,logger = logger,dry_run=args.dry_run)

if not os.path.exists(dest):
    logger.info("MISSING destintion_dir-->"+dest+"<-- ")
    os.makedirs(dest)

    origin_branches = util.get_branches(args.origin, branch_selection=args.branches)

    dev_git.init()

    dev_git.get_remotes()
    dev_git.add_remote(args.origin, name='origin', fetch_branches=origin_branches)
    dev_git.add_remote(args.upstream, name='upstream')

    upstream_branches = util.get_branches(
        args.upstream,
        branch_pattern='.*?\s+refs/pull/([0-9]*?)/head\s+',
        # branch_exclude_pattern='.*?\s+refs/pull/({branch})/merge\s+',
        branch_format_string='pull/{branch}/head',
        branch_selection=args.prlist)

    local_pr=util.trasf_match(upstream_branches,in_match='.*/([0-9]*)/(.*)',out_format='pull/{name}/clean')

    dev_git.fetch(name='origin',branches=origin_branches)

    if args.integration:
        if len(origin_branches) > 0 :
            upstream_clean = origin_branches[0]
            print("--------------------------------------"+upstream_clean+"-----------------------")
            dev_git.checkout(upstream_clean)
            dev_git.sync_upstream()
            dev_git.checkout(upstream_clean,newbranch=args.master)

            dev_git.sync_upstream()

            for b in origin_branches[1:] :
                dev_git.checkout(b)
                dev_git.sync_upstream(options=['--rebase'])

            dev_git.fetch(name='upstream',branches=local_pr)

            for n,branch in local_pr.items():
                logger.info("local_pr "+ n+" "+branch)
                dev_git.checkout(branch,newbranch=branch+'_update')
                dev_git.merge(upstream_clean,comment='sync with upstream develop ')
                dev_git.checkout(args.master)
                dev_git.merge(branch+'_update',comment='merged '+branch)

            for branch in origin_branches[1:] :
                dev_git.checkout(args.master)
                dev_git.merge(branch,comment='merged '+branch)
    else:
        dev_git.checkout(args.master)

else:
    logger.info("Folder ->"+dest+"<- already existing")
    if args.update:
        logger.info("Updating Folder ->"+dest+"<-")
        pull_options=[]
        for flag in args.pull_flags : pull_options.append('--'+flag)
        for b in dev_git.get_local_branches():
            dev_git.checkout(b)
            dev_git.sync_upstream(upstream='origin', master=b,options=pull_options)

########## cache handling ##############
cachedir=args.cache
if not os.path.exists(cachedir):
    cachedir=os.path.join(root_dir,cachedir)
else:
    cachedir=os.path.abspath(cachedir)
if not os.path.exists(cachedir):
    os.makedirs(cachedir)
logger.info("cache_dir-->"+cachedir+"<--")
if os.path.exists(os.path.join(dest, 'var', 'spack')):
    deploy_cache=os.path.join(dest, 'var', 'spack','cache')
    logger.info("deploy cache_dir-->"+deploy_cache+"<--")
    if not os.path.exists(deploy_cache):
        os.symlink(cachedir,deploy_cache)
        logger.info("symlinked -->"+cachedir+"<-->"+deploy_cache)

########## install handling ##############
if  args.install:
    logger.info("find install in args-->"+args.install+"<--")
    install = args.install
    if not os.path.exists(install):
        install = os.path.join(root_dir,args.install)
        if not os.path.exists(install):
            install = os.path.join(dest,args.install)
else:
    install = os.path.join(dest,'opt','spack')
if not os.path.exists(install):
    logger.info("creting install_dir-->"+install+"<--")
    os.makedirs(install)
logger.info("install_dir-->"+install+"<--")

me=util.myintrospect(tags={'calori': 'ws_mint', 'galileo':'galileo', 'marconi':'marconi' })

logger.info("config-->"+args.config+"<--")
configpar=args.config
config_path_list=[]
configdir=os.path.abspath(os.path.join(configpar,'config'))
if os.path.exists(configdir):
    if not configdir in config_path_list:
        config_path_list=[configdir]+config_path_list
        logger.info("config_dir-->"+configdir+"<-- ADDED")

configdir=os.path.join(root_dir,configpar,'config')
if os.path.exists(configdir):
    if not configdir in config_path_list:
        config_path_list=[configdir]+config_path_list
        logger.info("config_dir-->"+configdir+"<-- ADDED")

if not configpar:
    configpar=me.platform_tag()
    if configpar:
        configdir=os.path.join(root_dir,'recipes','hosts',configpar,'config')
if os.path.exists(configdir):
    if not configdir in config_path_list:
        config_path_list=[configdir]+config_path_list
        logger.info("config_dir-->"+configdir+"<-- ADDED")

########## apply config#########
if args.clearconfig:
    spack_config_dir=os.path.join(dest,'etc','spack')
    logger.info("Clear config Folder ->"+spack_config_dir+"<-")
    for f in glob.glob(spack_config_dir+ "/*.yaml"):
        os.remove(f)


subst=dict()
subst["RCM_DEPLOY_ROOTPATH"] = root_dir
subst["RCM_DEPLOY_INSTALLPATH"] = install
subst["RCM_DEPLOY_SPACKPATH"] = dest
for p in config_path_list:
    logger.info("config_dir-->"+p+"<-- ")
    for f in glob.glob(p+ "/*.yaml"): # generator, search immediate subdirectories
        outfile=os.path.basename(f)
        target=os.path.join(dest,'etc','spack',outfile)
        logger.info("config_file "+outfile+" -->"+f+"<-- ")
        if not os.path.exists(target):
            templ= mytemplate.stringtemplate(open(f).read())
            out=templ.safe_substitute(subst)
            logger.info("WRITING config_file "+outfile+" -->"+target+"<-- ")
            open(target,"w").write(out)

util.source(os.path.join(dest,'share','spack','setup-env.sh'))
for p in config_path_list:
    initfile=os.path.join(p,'config.sh')
    if os.path.exists(initfile):
        logger.info("parsing init file-->" + initfile + "<-- ")
        f=open(initfile,'r')
        for line in f:
            if len(line)>0:
                if not line[0] == '#':
                    templ= mytemplate.stringtemplate(line)
                    cmd=templ.safe_substitute(subst)
                    (ret,out,err)=util.run(cmd.split(),logger=logger)
                    logger.info("  " + out )



