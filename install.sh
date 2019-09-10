#! /bin/bash

INST_DIR=/usr/local/eSEAT
MKDIR="/usr/bin/sudo /bin/mkdir -p "
CP="/usr/bin/sudo /bin/cp "
#FILES="seatml.xsd rtc.conf"
#FILES="etc/rtc.conf etc/template.seatml etc/setup.bash eSEAT.py eSEAT_Node.py"
FILES="etc/rtc.conf etc/template.seatml etc/setup.bash"
DIRS="html libs 3rd_party examples bin ros_samples"

echo "Install Python2"
sudo apt-get -y install python-pip python-tk python-yaml python-lxml

echo "Install eSEAT"
sudo python setup_py2.py install

[ -d $INST_DIR ] || $MKDIR $INST_DIR

for f in $FILES; do
  $CP $f $INST_DIR
done

for d in $DIRS; do
  $CP -r $d $INST_DIR
done
