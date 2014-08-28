#!/bin/ksh

# We assume we are at the <git-working-dir>/graphite-web-sfdc/webapp directory
# and the directory to keep the tar ball is at <git-working-dir>/deploy
Git_Top_level_Dir=`git rev-parse --show-toplevel`
Total_Fields=`echo $Git_Top_level_Dir|awk 'BEGIN {FS="/"} ; END{print NF}'`
((NF=Total_Fields-1))
Git_Work_Dir=`echo $Git_Top_level_Dir|cut -d'/' -f1-${NF}`
Git_Deploy_Dir="${Git_Work_Dir}/deploy"
mkdir -p ${Git_Deploy_Dir}
DATE=`date '+%Y%m%d'`

# Compile all python code first
python -m compileall graphite

# Now package
for dir in content graphite
do
     tar zcf ${Git_Deploy_Dir}/${dir}.deploy.${DATE}.tar.gz ./${dir}
     if [ $? -eq 0 ];then
          echo "Deploy tar ball ${Git_Deploy_Dir}/${dir}.deploy.${DATE}.tar.gz successfully created"
     else
          echo "Error in creating deploy tar ball ${Git_Deploy_Dir}/${dir}.deploy.${DATE}.tar.gz"
     fi
done
