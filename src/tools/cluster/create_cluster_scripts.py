#!/misc/local/python3/bin/python3.5

import os

script_base = """\
#!/bin/sh
export KTXSRC='/home/schauderd/mouselight/KTX/pyktx/src'
export PYTHONPATH="$KTXSRC"
echo $PYTHONPATH
/misc/local/python3/bin/python3.5 $KTXSRC/tools/convert_subtree.py "%s" "%s" "%s" %d
"""

# input_root = "/nobackup2/mouselight/2016-04-04b"
# input_root = "/nobackup2/mouselight/2016-07-18b"
# input_root = "/nrs/mltest/161025b"
input_root = "/nrs/mouselight/SAMPLES/2017-04-19"
# input_root = "/groups/dickson/dicksonlab/BenArthur/20170217_10ExM"
# output_root = "/nobackup2/mouselight/brunsc/ktxtest"
output_root = "/nrs/mouselight/schauderd/ktxtest"
# NO CHANGES NECESSARY BEYOND THIS POINT TO CUSTOMIZE THIS SCRIPT

# output_root = "/groups/dickson/dicksonlab/CMBruns/ktx"
subtree_depth = 3

def recurse_octree(folder, level, specimen_name):
    if not os.path.exists(folder):
        return
    # if level > 4:
    #     return
    if level == 1 or level % subtree_depth == 2: # just levels 2 and 5 (we'll fill in level 1 manually)
        print (folder)
        if level == 1:
            subtree0 = []
        else:
            subtree0 = folder.split('/')[-(level-1):]
        subtree = "/".join(subtree0)
        print (subtree)
        script = script_base % (input_root, output_root, subtree, subtree_depth)
        # print (script)
        script_name = "subtree%s.sh" % "".join(subtree0)
        print (script_name)
        if True:
            f = open('jobscripts_%s/%s' % (specimen_name, script_name), 'w')
            f.write(script)
            f.close()
    # return
    for i0 in range(8):
        subfolder = folder + '/' + str(i0+1)
        recurse_octree(subfolder, level + 1, specimen_name)

specimen_name = input_root.split('/')[-1]
print (specimen_name)
try:
    os.makedirs("jobscripts_%s" % specimen_name)
except:
    pass
recurse_octree(input_root, 1, specimen_name)

