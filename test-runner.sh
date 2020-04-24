#!/usr/bin/env bash

# run tests through docker-compose
docker-compose up --abort-on-container-exit

# check last docker-compose status
# rabbit stops with 143 exit code
if [[ -z "$TRAVIS" ]]; then
    docker-compose down -v &
fi
CODE=`docker-compose ps -q | xargs -I{} docker inspect -f '{{ .State.ExitCode }}' {} | grep -vE '(0|3|143)' | wc -l | tr -d ' '`

echo "Tests completed with exit code $CODE"

# exit with last code
exit $CODE
