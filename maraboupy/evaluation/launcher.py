import os
import sys
import subprocess
from datetime import datetime
import json
import itertools
import argparse
import numpy as np
import CnnAbs
import shutil

####################################################################################################
####################################################################################################
####################################################################################################

def globalTimeOut():
    return 1,0,0

TIMEOUT_H, TIMEOUT_M, TIMEOUT_S = globalTimeOut()
TIME_LIMIT = "{}:{:02d}:{:02d}".format(TIMEOUT_H, TIMEOUT_M + 2, TIMEOUT_S)    

####################################################################################################
####################################################################################################
####################################################################################################

def experimentAbsPolicies(numRunsPerType, commonFlags, batchDirPath, slurm=False, gtimeout=None):
    runCmds = list()
    runTitles = list()
    title2Label = dict()

    for policy in CnnAbs.Policy.allPolicies():
        title2Label["{}Cfg".format(policy)] = "{}".format(policy)
        for i in range(numRunsPerType):
            title = "{}Cfg---{}".format(policy, i)
            cmd = commonFlags + ["--policy", policy, "--sample", str(i)]
            cmd += ["--run_title", title]
            runCmds.append(cmd)
            runTitles.append(title)

    with open(batchDirPath + "/plotSpec.json", 'w') as f:
        policiesCfg = ["{}Cfg".format(policy) for policy in CnnAbs.Policy.abstractionPolicies()]
        jsonDict = {"Experiment"  : "CNN Abstraction Vs. Vanilla Marabou",
                    "TIMEOUT_VAL" : gtimeout,
                    "title2Label" : title2Label,
                    "COIRatio"    : policiesCfg,
                    "compareProperties": list(itertools.combinations(policiesCfg, 2)) + [('VanillaCfg', policy) for policy in policiesCfg],
                    "commonRunCommand" : " ".join(commonFlags),
                    "runCommands"  : [" ".join(cmd) for cmd in runCmds],
                    "xparameter" : "cfg_sampleIndex"}
        json.dump(jsonDict, f, indent = 4)

    return runCmds, runTitles

def experimentDifferentDistances(numRunsPerType, commonFlags, batchDirPath, slurm=False, gtimeout=None):
    runCmds = list()
    runTitles = list()
    title2Label = dict()

    distance = [round(x, 3) for x in np.linspace(0.025, 0.2, num=numRunsPerType)]
    

    for policy in CnnAbs.Policy.allPolicies():
        title2Label["{}Cfg".format(policy)] = "{}".format(policy)
        for i in range(numRunsPerType):
            title = "{}Cfg---{}".format(policy, str(distance[i]).replace('.','-'))
            runCmds.append(commonFlags + ["--run_title", title, "--prop_distance", str(distance[i]), "--policy", policy])
            runTitles.append(title)

    if slurm:
        with open(batchDirPath + "/plotSpec.json", 'w') as f:
            policiesCfg = ["{}Cfg".format(policy) for policy in CnnAbs.Policy.abstractionPolicies()]
            jsonDict = {"Experiment"  : "Different property distances on the same sample",
                        "TIMEOUT_VAL" : gtimeout,
                        "title2Label" : title2Label,
                        "COIRatio"    : policiesCfg,
                        "compareProperties": list(itertools.combinations(policiesCfg, 2)) + [('VanillaCfg', policy) for policy in policiesCfg],
                        "commonRunCommand" : " ".join(commonFlags),
                        "runCommands"  : [" ".join(cmd) for cmd in runCmds],
                        "xparameter" : "cfg_distance"}
            json.dump(jsonDict, f, indent = 4)

    return runCmds, runTitles

def runSingleRun(cmd, title, basePath, batchDirPath, pyFilePath):

    CPUS = 8
    MEM_PER_CPU = "8G"
    
    runDirPath = batchDirPath + "/" + title
    os.makedirs(runDirPath, exist_ok=True)
    os.chdir(runDirPath)

    sbatchCode = list()
    sbatchCode.append("#!/bin/bash")
    sbatchCode.append("#SBATCH --job-name={}".format(title))
    sbatchCode.append("#SBATCH --cpus-per-task={}".format(CPUS))
    sbatchCode.append("#SBATCH --mem-per-cpu={}".format(MEM_PER_CPU))
    sbatchCode.append("#SBATCH --output={}/cnnAbsTB_{}.out".format(runDirPath, title))
    sbatchCode.append("#SBATCH --partition=long")
    sbatchCode.append("#SBATCH --signal=B:SIGUSR1@300")
    sbatchCode.append("#SBATCH --time={}".format(TIME_LIMIT))
    sbatchCode.append("#SBATCH -C avx2")
    #sbatchCode.append("#SBATCH --reservation 5781")    
    sbatchCode.append("")
    sbatchCode.append("pwd; hostname; date")
    sbatchCode.append("")
    sbatchCode.append("csh {}".format(CnnAbs.CnnAbs.marabouPath + "/../py_env/bin/activate.csh"))
    sbatchCode.append("export PYTHONPATH=$PYTHONPATH:{}:{}".format(CnnAbs.CnnAbs.maraboupyPath, CnnAbs.CnnAbs.marabouPath))
    sbatchCode.append("export GUROBI_HOME={}".format(os.path.abspath(CnnAbs.CnnAbs.marabouPath + "/../gurobi911/linux64")))
    sbatchCode.append("export PATH=$PATH:${GUROBI_HOME}/bin")
    sbatchCode.append("export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${GUROBI_HOME}/lib")
    sbatchCode.append("export GRB_LICENSE_FILE=/cs/share/etc/license/gurobi/gurobi.lic")
    sbatchCode.append("")
    sbatchCode.append("")
    sbatchCode.append('echo "Ive been launched" > {}/Started'.format(runDirPath))        
    sbatchCode.append("stdbuf -o0 -e0 python3 {} {}".format(pyFilePath, " ".join(cmd)))
    sbatchCode.append("")
    sbatchCode.append("date")

    sbatchFile = runDirPath + "/" + "cnnAbsRun-{}.sbatch".format(title)
    with open(sbatchFile, "w") as f:
        for line in sbatchCode:
            f.write(line + "\n")

    os.chdir(basePath)            
    print("Running : {}".format(" ".join(["sbatch", sbatchFile])))
    subprocess.run(["sbatch", sbatchFile]) 

####################################################################################################
####################################################################################################
####################################################################################################

def main():
    
    experiments = {"AbsPolicies"    : experimentAbsPolicies,
                   "DifferentDistances" : experimentDifferentDistances}
    parser = argparse.ArgumentParser(description='Launch Sbatch experiments')
    parser.add_argument("--exp",           type=str, default="AbsPolicies", choices=list(experiments.keys()), help="Which experiment to launch?", required=False)
    parser.add_argument("--runs_per_type", type=int, default=100, help="Number of runs per type.")
    parser.add_argument("--sample",        type=int, default=0, help="For part of experiments, specific sample choice")
    parser.add_argument("--net",           type=str, help="Network to verify", required=True)
    parser.add_argument("--pyFile",           type=str, help="Python script path", required=True)    
    parser.add_argument("--prop_distance", type=float, default=0.03,                    help="Distance checked for adversarial robustness (L1 metric)") 
    parser.add_argument('--slurm'   , dest='slurm', action='store_true',  help="Launch Cmds in Slurm")
    parser.add_argument("--abstract_first", dest='abstract_first', action='store_true' , help="Abstract the first layer (used for specific experiment)")
    parser.add_argument("--propagate_from_file", dest='propagate_from_file', action='store_true' , help="Read propagated bounds from file.")
    parser.add_argument("--batchDir",      type=str, help="Directory to locate experiment logs in.", default='')
    parser.add_argument("--gtimeout",      type=int, default=-1, help="Individual timeout for each verification run.")    
    args = parser.parse_args()
    experiment = args.exp
    numRunsPerType = args.runs_per_type
    experimentFunc = experiments[experiment]
    net = args.net
    prop_distance = args.prop_distance
    pyFilePath = os.path.abspath(args.pyFile)
    slurm = args.slurm
    abstract_first = args.abstract_first
    propagate_from_file = args.propagate_from_file


    gtimeout = TIMEOUT_H * 3600 + TIMEOUT_M * 60 + TIMEOUT_S
    if args.gtimeout != -1:
        gtimeout = args.gtimeout
    
    ####################################################################################################
    
    timestamp = datetime.now()
    if args.batchDir:
        batchId = args.batchDir
    else:
        batchId = "_".join(filter(None, [experiment, net.split('/')[-1].replace('.h5',''), timestamp.strftime("%d-%m-%y"), timestamp.strftime("%H-%M-%S")]))
    basePath = CnnAbs.CnnAbs.maraboupyPath + "/"
    batchDirPath = basePath + "logs_CnnAbs/" + batchId
    if os.path.exists(batchDirPath):
        shutil.rmtree(batchDirPath, ignore_errors=True)
    os.makedirs(batchDirPath, exist_ok=True)
    with open(batchDirPath + "/runCmd.sh", 'w') as f:
        f.write(" ".join(["python3"]+ sys.argv) + "\n")

    commonFlags = ["--gtimeout", str(gtimeout)]
    commonFlags += ["--batch_id", batchId]
    if experiment != 'DifferentDistances':
        commonFlags += ["--prop_distance", str(prop_distance)]
    else:
        commonFlags += ["--sample", str(args.sample)]
    commonFlags += ["--net", net]
    if abstract_first:
        commonFlags += ["--abstract_first"]
    if propagate_from_file:
        commonFlags += ["--propagate_from_file"]
        
    runCmds, runTitles = experimentFunc(numRunsPerType, commonFlags, batchDirPath, slurm=slurm, gtimeout=gtimeout)
    
    sbatchFiles = list()
    cmdJson = list()
    for cmd, title in zip(runCmds, runTitles):
        if slurm:
            runSingleRun(cmd, title, basePath, batchDirPath, pyFilePath)
        cmdJson.append("python3 {} {}".format(pyFilePath, " ".join(cmd)))
    with open(batchDirPath + "/launcherCmdList.json", 'w') as f:
        json.dump(cmdJson, f, indent=4)        
    with open(batchDirPath + "/launcherCmdList", 'w') as f:
        for line in cmdJson:
            f.write(line + '\n')
                
if __name__ == "__main__":
    main()    