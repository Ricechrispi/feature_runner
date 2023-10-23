#!/usr/bin/env bash
echo "c o CALLSTR ${@}"

#TODO adapt these paths! also point in feature_setup to this file as "executable"
base_dir="/home/guests/cpriesne"
conda_location="/home/guests/cpriesne/miniconda3"
conda_env_name="rb" # name of conda environment, default should be "rb"

INSTANCE=""
INSTANCE_FOLDER=""
COMBINED_FILE=""

while [[ $# -gt 0 ]]; do
  case $1 in
  -i | --instance)
    shift
    INSTANCE="${1}"
    shift
    ;;
  -I | --instance_folder)
    shift
    INSTANCE_FOLDER="${1}"
    shift
    ;;
  -c | --combined_file)
    shift
    COMBINED_FILE="${1}"
    shift
    ;;
  *) # unknown argument
    echo "c o Unknown argument: ${1}"
    exit 1
    ;;
  esac
done


echo "c o ================= TEST ENV VARS ======================"
echo "c o ENV INSTANCE = ${INSTANCE}"
echo "c o ENV INSTANCE_FOLDER = ${INSTANCE_FOLDER}"
echo "c o ENV COMBINED_FILE = ${COMBINED_FILE}"

echo "c o ================= SET PRIM INTRT HANDLING ============"
function interrupted() {
  echo "c o Sending kill to subprocess"
  kill -TERM $PID
}
trap interrupted TERM
trap interrupted INT

echo "c o ================= Changing directory ==================="
cd "${base_dir}"
if [[ $? -ne 0 ]]; then
  echo "c o Could not change directory to ${base_dir}. Exiting..."
  exit 1
fi

echo "c o ================= Activating Conda environment ======================"
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('${conda_location}/bin/conda' 'shell.bash' 'hook' 2>/dev/null)"
if [ $? -eq 0 ]; then
  eval "$__conda_setup"
else
  if [ -f "${conda_location}/etc/profile.d/conda.sh" ]; then
    . "${conda_location}/etc/profile.d/conda.sh"
  else
    export PATH="${conda_location}/bin:$PATH"
  fi
fi
unset __conda_setup
conda activate "$conda_env_name"

echo "c o ================= Building Command String ============"
cmd="python feature_runner.py"
if [[ -n "${INSTANCE}" ]]; then
  cmd+=" --instance ${INSTANCE}"
fi
if [[ -n "${INSTANCE_FOLDER}" ]]; then
  cmd+=" --instance_folder ${INSTANCE_FOLDER}"
fi
if [[ -n "${COMBINED_FILE}" ]]; then
  cmd+=" --combined_file ${COMBINED_FILE}"
fi
echo "c o SOLVERCMD=$cmd"

echo "c o ================= Running Feature calc ====================="
myenv="TMPDIR=$TMPDIR"
#env $myenv $cmd >$tmpfile &
env $myenv $cmd &
PID=$!
wait $PID
exit_code=$?
echo "c o ================= Done ========================"
echo "c o feature_wrapper: Finished with exit code=${exit_code}"
echo "c f RET=${exit_code}"

exit $exit_code
