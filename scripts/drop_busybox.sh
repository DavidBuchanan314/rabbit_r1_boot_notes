#!/bin/sh

if [ "$#" -ne 1 ]; then
	echo "USAGE: ./$0 rabbit_ip_address";
	exit;
fi

(
	echo "base64 -d <<EOF | gunzip > /dev/busybox";
	curl "https://raw.githubusercontent.com/EXALAB/Busybox-static/main/busybox_arm64" | gzip | base64;
	echo "EOF";
	echo "chmod +x /dev/busybox"
	echo "/dev/busybox telnetd -l /system/bin/sh -p 31337";
	echo "echo done (press Ctrl+C to exit)";
) | nc $1 1337
