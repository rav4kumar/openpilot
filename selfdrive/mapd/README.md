Instructions to get cached offline maps:

Android Root: just install Termux and install arch linux and intall docker

Android Non Root:
Intall Termux from the play store
run
pkg install termux-tools proot util-linux net-tools openssh git coreutils wget

wget https://raw.githubusercontent.com/xeffyr/termux-x-repository/master/enablerepo.sh
bash enablerepo.sh 

and 

pkg install qemu-system-x86_64 --fix-missing

to intall qemu

run 

termux-setup-storage 

to setup storage access

mkdir termux-docker && cd termux-docker
git clone https://github.com/pwdonald/chromeos-qemu-docker

cd storage/external-1

to get to the external storage

pkg install qemu-utils

qemu-img create -f qcow2 virtual_drive 16G

curl -sL http://dl-cdn.alpinelinux.org/alpine/v3.7/releases/x86_64/alpine-virt-3.7.3-x86_64.iso -o alpine_x86_64.iso

to download the alpine virutal distro

qemu-system-x86_64 -nographic -m 512m -cdrom alpine_x86_64.iso -hda virtual_drive -boot d -net nic -net user

to start the intallation. Use mbr sys

run setup-alpine 

If you encounter internet related errors, use google dns withecho 'nameserver 8.8.8.8' > /etc/resolv.conf and run setup-alpine again.

Once done, exit the virtual machine with Ctrl-A X.

create a swap file.

qemu-img create -f qcow2 virtual_swap 8G

to run the VM use this command

qemu-system-x86_64 -nographic -hda virtual_drive -boot c -net user,hostfwd=tcp::10022-:22,hostfwd=tcp::10080-:80,hostfwd=tcp::12345-:12345 -net nic -hdb virtual_swap -m 2048M -smp 3

This can take a few minutes to start up so just be patient

apk add vim

apk update

vim /etc/apk/repositories
to enable community features

apk add wget

apk add docker

in
/etc/update-extlinux.conf
add
default_kernel_opts="... cgroup_enable=memory swapaccount=1"
and
update-extlinux

check
docker info
to see that everything is working correctly

setup hdb as a linux swap partition with fdisk. That should give you 10GB of total RAM.

service docker start

use the https://github.com/wiktorn/Overpass-API

docker pull wiktorn/overpass-api

docker run \
-e OVERPASS_META=yes \
-e OVERPASS_MODE=init \
-e OVERPASS_PLANET_URL=http://download.geofabrik.de/europe/germany/baden-wuerttemberg/tuebingen-regbez-latest.osm.bz2 \
-e OVERPASS_DIFF_URL=http://download.geofabrik.de/europe/germany/baden-wuerttemberg/tuebingen-regbez-updates/ \
-e OVERPASS_RULES_LOAD=10 \
-v /big/docker/overpass_db/:/db \
-p 12345:80 \
-i -t \
--name overpass_bw wiktorn/overpass-api

docker start overpass_bw and docker stop overpass_bw can now start the docker process

This is a 100MB file and lands up using about 6GB of RAM and HDD space after the inital install it only requires 1GB to actively runn

