export MAMBA_ROOT_PREFIX=/home/claude/gz/mamba
eval "$(/home/claude/gz/bin/micromamba shell hook -s bash)"
micromamba activate ros
export ROS_DOMAIN_ID=7
export ROS_LOCALHOST_ONLY=1
export GZ_IP=127.0.0.1
