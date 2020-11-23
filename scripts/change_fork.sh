DATA_DIR="/data/"
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color
DIRECTORIES=""

show_options()
{
echo -e "\n------------------\n"
echo -e "What do you want to do"
echo -e "1. Backup Current Fork"
echo -e "2. Restore Existing Backup"
echo -e "3. Show Current Forks"
echo -e "4. Reboot Eon"
echo -e "5. Exit"
}



show_forks()
{
SEQ=0
DIRECTORIES=""
echo -e "\nFound the below forks in the $DATA_DIR directory"
echo -e "------------------"
echo -e "Seq\tFork Name\tBranch Name\tDirectory Name"
for DIR in `find ${DATA_DIR} -type d -maxdepth 1 -exec  test -e '{}/.git' ';' -print -prune`; do
  cd ${DIR}
  git remote get-url origin > /dev/null 2>&1
  if [ $? -ne 0 ]; then 
    continue;
  fi
  SEQ=$((SEQ+1))
  FORK_NAME=`basename $(git remote get-url origin 2>/dev/null) .git 2>/dev/null`
  CURRENT_BRANCH=`basename $(git symbolic-ref HEAD 2>/dev/null) 2>/dev/null`
  BASENAME_DIR=`basename $DIR`
  DIRECTORIES="${DIRECTORIES}${BASENAME_DIR}|"
  if [[ `basename $DIR` == "openpilot" ]]; then
     echo -e "${GREEN}${SEQ}\t${FORK_NAME}\t$CURRENT_BRANCH\t${BASENAME_DIR}${NC}"
  else
     echo -e "${RED}${SEQ}\t${FORK_NAME}\t$CURRENT_BRANCH\t${BASENAME_DIR}${NC}"
  fi
done
}




while true; do
  show_options	
  read -p 'Option: ' OPTION 
  if [ $OPTION -eq 1 ];then
     CURRENT_TIMESTAMP=`date +'%Y%d%m%H%M'`
     echo -e "Backup In Progress.. Backup can take several minutes"
     cp -R "${DATA_DIR}/openpilot" "${DATA_DIR}/openpilot_BKP_${CURRENT_TIMESTAMP}"
     echo -e "Backup Completed"
     continue
  elif [ $OPTION -eq 2 ];then
     show_forks
     echo -e "Please input the version you want to restore"
     read -p 'Seq: ' OPTION2
     RESTORE_DIR=`echo ${DIRECTORIES} | cut -d "|" -f${OPTION2}`
     if [ ${RESTORE_DIR} == "openpilot" ]; then 
       echo -e "\nCannot select the current version"
       continue;
     fi
     echo -e "Restoring the version you selected"
     CURRENT_TIMESTAMP=`date +'%Y%d%m%H%M'`
     mv "${DATA_DIR}/openpilot" "${DATA_DIR}/openpilot_BKP_${CURRENT_TIMESTAMP}"
     mv "${DATA_DIR}/${RESTORE_DIR}" "${DATA_DIR}/openpilot"
     echo -e "Restore Completed"
     show_forks
     continue
  elif [ $OPTION -eq 3 ];then
     show_forks
     continue
  elif [ $OPTION -eq 4 ];then
     reboot	
  elif [ $OPTION -eq 5 ];then
     exit 
  else
     echo "Invalid Option"
     continue
  fi
done
