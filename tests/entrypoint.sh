echo "Starting entrypoint.sh"
mkdir /tmp/backup-dest
echo "Extracting backup.tar.gz"
tar xvf /tmp/backup.tar.gz --directory /tmp/backup-dest
echo "Moving data to /config"
mv /tmp/backup-dest/data/.* /tmp/backup-dest/data/* -t /config
echo "Starting the original entrypoint /init"
