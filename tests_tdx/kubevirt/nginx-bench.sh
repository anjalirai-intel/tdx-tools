#!/bin/bash

set +e  # not quit for failure command
set -x

# Stop nginx container if need (optional)
docker rm tdx-nginx

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
docker rm tdx-nginx
exit $ret
