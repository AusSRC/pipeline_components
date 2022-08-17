# CADC VOS

Bash scripts and container for transferring files to the CADC VOSpace

## Authenticate

To use you will first need to get a CADC certificate. You can do this by running

```
cadc-get-cert -u <username>
```

here you will be prompted for a password. This will store a CADC certificate at `$HOME/.ssl/cadcproxy.pem`. Once you have the certificate you will be able to run the `vos` commands.

## CLI

We have a script with commands for copying the file of interest and setting the correct permissions

```
./copy.sh <file> <directory>
```

- `file`: File that you would like to transfer
- `directory`: Folder within the VOSpace to move the file

## Docker

To run the image there will be an additional step to mount the volume containing the CADC certificate and the file of interest to the container.

```
docker run \
    -v $HOME/.ssl/cadcproxy.pem:/root/.ssl/cadcproxy.pem \
    -v file.txt:/app/file.txt
    cadc-vos-copy:latest file.txt dockertest
```
