from flask import Flask, request, make_response
from flask_restful import Resource, Api, abort, reqparse
from flask_restful_swagger import swagger
from flask_cors import CORS
import math
import logging
import fire
import os
from functools import wraps
import shutil

LOGGER = logging.getLogger(__name__)

DATA_DIR = "../data"

INSTANCES = {}

# list folder of DATA_DIR
def get_instances():
    for dir in os.listdir(DATA_DIR):
        if os.path.isdir(os.path.join(DATA_DIR, dir)):
            INSTANCES[dir] = {
                "id": dir,
                "absolutePath": os.path.join(DATA_DIR, dir),
                "label": dir,
            }
            
def validate(actual_method):
    @wraps(actual_method)  # preserves signature
    def wrapper(*args, **kwargs):
        # do your validation here
        get_instances()
        return actual_method(*args, **kwargs)

    return wrapper

def abort_if_Instance_doesnt_exist(instance_id):
    if instance_id not in INSTANCES:
        abort(404, message="Instance {} doesn't exist".format(instance_id))

parser = reqparse.RequestParser()
parser.add_argument('instance')


# Instance
# shows a single Instance item and lets you delete a Instance item
class Instance(Resource):
    @validate
    def get(self, instance_id):
        abort_if_Instance_doesnt_exist(instance_id)
        return INSTANCES[instance_id]

    @validate
    def delete(self, instance_id):
        abort_if_Instance_doesnt_exist(instance_id)
        path = INSTANCES[instance_id]["absolutePath"]
        # delete directory path recursivly
        shutil.rmtree(path)
        del INSTANCES[instance_id]
        return '', 204

    @validate
    def put(self, instance_id):
        args = parser.parse_args()
        instance = {'instance': args['instance']}
        INSTANCES[instance_id] = instance
        return instance, 201


# InstanceList
# shows a list of all Instances, and lets you POST to add new tasks
class InstanceList(Resource):
    @validate
    def get(self):
        return INSTANCES

    @validate
    def post(self):
        args = parser.parse_args()
        print(args)


        # instance_id = args['id']
        
        # if instance_id in INSTANCES:
        #     abort(404, message="Instance {} already exist".format(instance_id))

        # #INSTANCES[instance_id] = {}

        # # make folder in DATA_DIR
        # path = os.path.join(DATA_DIR, instance_id)
        # os.makedirs(path)
        # get_instances()
        
        #return INSTANCES[instance_id], 201


class HelloWorld(Resource):
    def get(self):
        return {'hello': 'world'}

def backend(
    port=int(os.environ.get("PORT", 8080)),
    debug=True
):
    """main entry point"""

    app = Flask(__name__)
    api = swagger.docs(Api(app), apiVersion='0.1')
    api.add_resource(HelloWorld, '/')
    api.add_resource(InstanceList, '/instances')
    api.add_resource(Instance, '/instance/<instance_id>')


    CORS(app)
    LOGGER.info("starting!")
    app.run(host="0.0.0.0", port=port, debug=debug)

if __name__ == '__main__':
    fire.Fire(backend)
