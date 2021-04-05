# file_catalog
Store file metadata information in a file catalog

[![CircleCI](https://circleci.com/gh/WIPACrepo/file_catalog/tree/master.svg?style=shield)](https://circleci.com/gh/WIPACrepo/file_catalog/tree/master)


## Prerequisites
To get the prerequisites necessary for the file catalog:

    pip install -r requirements.txt



## Running the server
To start an instance of the server running:

    python -m file_catalog



## Running the unit tests
To run the unit tests for the service, you need the
[CircleCI CLI](https://circleci.com/docs/2.0/local-cli/).
Then run it with:

    circleci local execute --job test



## Configuration
All configuration is done using environment variables.
To get the list of possible configuration parameters and their defaults, run

    python -m file_catalog --show-config-spec



## Interface
The primary interface is an HTTP server. TLS and other security
hardening mechanisms are handled by a reverse proxy server as
for normal web applications.



## Browser
Requests to the main url `/` are browsable like a standard website.
They will use javascript to activate the REST API as necessary.



## REST API
Requests with urls of the form `/api/RESOURCE` can access the
REST API. Responses are in [HAL](http://stateless.co/hal_specification.html)
JSON format.


### File-Entry Fields

#### File-Metadata Schema:
* _See [types.py](https://github.com/WIPACrepo/file_catalog/blob/master/file_catalog/schema/types.py)_

#### Mandatory Fields:
* `uuid` (provided by File Catalog)
* `logical_name`
* `locations` (with at least one non-empty URL)
* `file_size`
* `checksum.sha512`


### Route: `/api/files`
Resource representing the collection of all files in the catalog.


#### Method: `GET`
Obtain list of files

##### REST-Query Parameters
  * [`limit`](#limit)
  * [`start`](#start)
  * [`path` *or* `logical_name`](#path-shortcut-parameters)
  * [`directory`](#path-shortcut-parameters)
  * [`filename`](#path-shortcut-parameters)
  * [`path-regex`](#path-shortcut-parameters)
  * [`run_number`](#shortcut-parameter-run_number)
  * [`dataset`](#shortcut-parameter-dataset)
  * [`event_id`](#shortcut-parameter-event_id)
  * [`processing_level`](#shortcut-parameter-processing_level)
  * [`season`](#shortcut-parameter-season)
  * [`query`](#query)

##### HTTP Response Status Codes
  * `200`: Response contains collection of file resources
  * `400`: Bad request (query parameters invalid)
  * `429`: Too many requests (if server is being hammered)
  * `500`: Unspecified server error
  * `503`: Service unavailable (maintenance, etc.)

#### Method: `POST`
Create a new file or add a replica

  If a file exists and the checksum is the same, a replica
  is added. If the checksum is different a conflict error is returned.

##### REST-Query Parameters
  * `foo`

##### HTTP Response Status Codes
  * `200`: Replica has been added. Response contains link to file resource
  * `201`: Response contains link to newly created file resource
  * `400`: Bad request (metadata failed validation)
  * `409`: Conflict (if the file already exists); includes link to existing file
  * `429`: Too many requests (if server is being hammered)
  * `500`: Unspecified server error
  * `503`: Service unavailable (maintenance, etc.)

#### Method: `DELETE`
*Not supported*

#### Method: `PUT`
*Not supported*

#### Method: `PATCH`
*Not supported*


### Route: `/api/files/{uuid}`
Resource representing the metadata for a file in the file catalog.

#### Method: `GET`
Obtain file metadata information

##### REST-Query Parameters
  * `foo`

##### HTTP Response Status Codes
  * `200`: Response contains metadata of file resource
  * `404`: Not Found (file resource does not exist)
  * `429`: Too many requests (if server is being hammered)
  * `500`: Unspecified server error
  * `503`: Service unavailable (maintenance, etc.)

#### Method: `POST`
*Not supported*

#### Method: `DELETE`
Delete the metadata for the file

##### REST-Query Parameters
  * `foo`

##### HTTP Response Status Codes
  * `204`: No Content (file resource is successfully deleted)
  * `404`: Not Found (file resource does not exist)
  * `429`: Too many requests (if server is being hammered)
  * `500`: Unspecified server error
  * `503`: Service unavailable (maintenance, etc.)

#### Method: `PUT `
Fully update/replace file metadata information

##### REST-Query Parameters
  * `foo`

##### HTTP Response Status Codes
  * `200`: Response indicates metadata of file resource has been updated/replaced
  * `404`: Not Found (file resource does not exist) + link to “files” resource for POST
  * `409`: Conflict (if updating an outdated resource - use ETAG hash to compare)
  * `429`: Too many requests (if server is being hammered)
  * `500`: Unspecified server error
  * `503`: Service unavailable (maintenance, etc.)

#### Method: `PATCH`
Partially update/replace file metadata information

  The JSON provided as body to PATCH need not contain all the
  keys, only the keys that need to be updated. If a key is
  provided with a value null, then that key can be removed from
  the metadata.

##### REST-Query Parameters
  * `foo`

##### HTTP Response Status Codes
  * `200`: Response indicates metadata of file resource has been updated/replaced
  * `404`: Not Found (file resource does not exist) + link to “files” resource for POST
  * `409`: Conflict (if updating an outdated resource - use ETAG hash to compare)
  * `429`: Too many requests (if server is being hammered)
  * `500`: Unspecified server error
  * `503`: Service unavailable (maintenance, etc.)


### More About REST-Query Parameters

##### `limit`
- positive integer; number of results to provide *(default: 10k)*
- **NOTE:** The server *MAY* honor the `limit` parameter. In cases where the server does not honor the *limit* parameter, it should do so by providing fewer resources (`limit` should be considered the client’s upper limit for the number of resources in the response).

##### `start`
- non-negative integer; result at which to start at *(default: 0)*
- **NOTE:** the server *SHOULD* honor the `start` parameter
- **TIP:** increment `start` by `limit` to paginate many results

##### `query`
- MongoDB query; use to specify file-entry fields/ranges; forwarded to MongoDB daemon

##### Path-Shortcut Parameters
***In decreasing order of precedence...***
- `path-regex`
  - query by regex pattern (at your own risk... performance-wise)
  - equivalent to: `query: {"logical_name": {"$regex": p}}`

- `path` *or* `logical_name`
  - equivalent to: `query["logical_name"]`

- `directory`
  - query by absolute directory filepath
  - equivalent to: `query: {"logical_name": {"$regex": "^/your/path/.*"}}`
  - **NOTE:** a trailing-`/` will be inserted if you don't provide one
  - **TIP:** use in conjunction with `filename` (ie: `/root/dirs/.../filename`)

- `filename`
  - query by filename (no parent-directory path needed)
  - equivalent to: `query: {"logical_name": {"$regex": ".*/your-file$"}}`
  - **NOTE:** a leading-`/` will be inserted if you don't provide one
  - **TIP:** use in conjunction with `directory` (ie: `/root/dirs/.../filename`)

##### Shortcut Parameter: `run_number`
- equivalent to: `query["run.run_number"]`


##### Shortcut Parameter: `dataset`
- equivalent to: `query["iceprod.dataset"]`


##### Shortcut Parameter: `event_id`
- equivalent to: `query: {"run.first_event":{"$lte": e}, "run.last_event":{"$gte": e}}`


##### Shortcut Parameter: `processing_level`
- equivalent to: `query["processing_level"]`


##### Shortcut Parameter: `season`
- equivalent to: `query["offline_processing_metadata.season"]`



## Development

### Establishing a development environment
Follow these steps to get a development environment for the File Catalog:

    cd ~/projects
    git clone git@github.com:WIPACrepo/file_catalog.git
    cd file_catalog
    python3.7 -m venv ./env
    source env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

### Vagrant
To use Vagrant to set up a VM to run a File Catalog:

    vagrant up
    vagrant ssh
    cd file_catalog
    scl enable rh-python36 bash
    python -m venv ./env
    source env/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt

To use the VM in future sessions:

    vagrant up
    vagrant ssh
    cd file_catalog
    source env/bin/activate
    python -m file_catalog

### Unit testing
In case it comes in handy, the following command can be used to run
a single unit test. Replace the name of the test as necessary.

    circleci local execute --job test -e PYTEST_ADDOPTS='-s tests/test_files.py -k test_10_files'

Note that for a file to be picked up, it must be added to git first (with git add).

### Building a Docker container
The following commands will create a Docker container for the file-catalog:

    docker build -t file-catalog:{version} -f Dockerfile .
    docker image tag file-catalog:{version} file-catalog:latest

Where {version} is found in file_catalog/__init__py; e.g.:

    __version__ = '1.2.0'       # For {version} use: 1.2.0

### Pushing Docker containers to local registry in Kubernetes
Here are some commands to get the Docker container pushed to our Docker
register in our Kubernetes cluster:

    kubectl -n kube-system port-forward $(kubectl get pods --namespace kube-system -l "app=docker-registry,release=docker-registry" -o jsonpath="{.items[0].metadata.name}") 5000:5000 &
    docker tag file-catalog:{version} localhost:5000/file-catalog:{version}
    docker push localhost:5000/file-catalog:{version}
