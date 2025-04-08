#!/bin/bash

set +e  # not quit for failure command
set -x

while read env_var; do
  export "$env_var"
done < /etc/environment

echo "============Starting download go1.20.7.linux-amd64.tar.gz"
# download go
if [ -f /root/go1.20.7.linux-amd64.tar.gz ]; then
    rm /root/go1.20.7.linux-amd64.tar.gz
fi
wget -P /root https://go.dev/dl/go1.20.7.linux-amd64.tar.gz

echo "============Starting install go1.20.7.linux-amd64.tar.gz"
# uninstall old version
if [ -d /usr/local/go ]; then
    rm -rf /usr/local/go
fi

# install new version
tar -C /usr/local -xzf /root/go1.20.7.linux-amd64.tar.gz
echo "export PATH=$PATH:/usr/local/go/bin" >> /etc/profile
rm /root/go1.20.7.linux-amd64.tar.gz

go install github.com/codesenberg/bombardier@latest


# Stop nginx container if need (optional)
docker stop tdx-nginx || true
while docker container inspect tdx-nginx >/dev/null 2>&1; do sleep 1; done

# Run nginx container
docker run -d  --name tdx-nginx nginx
while true
do
   if docker ps -a --format '{{.Names}}' | grep -Eq "^tdx-nginx\$"; then
      break
   fi
   sleep 1
done

NGINX_IP=$(docker inspect -f '{{range.NetworkSettings.Networks}}{{.IPAddress}}{{end}}' tdx-nginx)

# Wait for nginx service fully running
count=0
while true
do
   </dev/tcp/$NGINX_IP/80
   if [[ $? == 0 ]]; then
      echo "Success start nginx-server in docker."
      break
   else
      ((count++))
      if (( $count > 10 )); then
         echo "Fail to run nginx service after 10 seconds. ret: $ret"
         exit 1
      fi
      echo "nginx server is not ready yet, wait for more seconds..."
      sleep 1
   fi
done

# Run benchmark
/root/go/bin/bombardier -c 125 -n 1000000 http://$NGINX_IP:80
ret=$?
if [[ $ret -eq 0 ]];
then
    echo "Success to run bombardier benchmark"
else
    echo "Fail to run bombardier benchmark, ret: $ret"
fi

# Clean up
docker stop tdx-nginx || true
exit $ret
