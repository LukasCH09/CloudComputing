#-------------------------------------
# Authors:
# - Arnaud Droxler
# - Lukas Bitter
#-------------------------------------

import errno
import os

from openstack import connection
from openstack import profile
from openstack import utils
from getpass   import getpass
from base64    import b64encode
import subprocess

AUTH_URL = 'http://hepiacloud.hesge.ch:5000/v3'

def create_connection(auth_url, project_name, username, password):
    auth_args = {
        'auth_url':auth_url, 
        'project_name':project_name, 
        'username':username, 
        'password':password, 
        'user_domain_name': 'default',
        'project_domain_name': 'default',
    }
    return connection.Connection(
        **auth_args
    )

def delete_server(conn, srv):
    print "Delete Server:"
    conn.compute.delete_server(srv)
    
def create_server(conn, name, img, flv, net, key, grp, userdata = ""):
    
    image = conn.compute.find_image(img)
    flavor = conn.compute.find_flavor(flv)
    network = conn.network.find_network(net)

    server = conn.compute.create_server(
        name=name, image_id=image.id, flavor_id=flavor.id,
        networks=[{"uuid": network.id}], key_name=key)

    #This method must wait until the instance is active
    print "Wait until the instance is active"
    server = conn.compute.wait_for_server(server)
    return server
    
def get_unused_floating_ip(conn):
    return conn.network.find_available_ip()    

def attach_floating_ip_to_instance(conn, instance, floating_ip):
    conn.compute.add_floating_ip_to_server(instance, floating_ip)

def main():
    print "Login phase..."
    project = "BitterLukasProject" #raw_input('Project:')
    username= "BitterLukas" #raw_input('Username:')
    password= "YTkyNjY1Nj" #getpass('Password:')
    conn = create_connection(AUTH_URL, project, username, password)
    print "Create MongoDB instance: "
    mongo = create_server(conn, 'mongoinstance', 'MongoDB Server clean install', 'm1.small', 'Network01', 'key_01', 'default')
    #print mongo
    print "Create RestClient instance: "
    userdata = '''#!/usr/bin/env bash
    nohup python /home/ubuntu/restclient.py %s & 
    ''' % mongo.addresses['Network01'][0]['addr'] 
    client = create_server(conn, 'clientinstance', 'RESTClient Clean install', 'm1.small', 'Network01', 'key_01', 'default', userdata)
    
    #print client
    print "Create RestServer instance: "
    userdata = '''#!/usr/bin/env bash
    nohup python /home/ubuntu/restserver.py %s %s %s &
    ''' % (mongo.addresses['Network01'][0]['addr'], project+':'+username, password)

    
    server = create_server(conn, 'serverinstance', 'RESTServer clean install', 'm1.small', 'Network01', 'key_01', 'default', userdata) 
    floating_ip = get_unused_floating_ip(conn)
    #print floating_ip
    attach_floating_ip_to_instance(conn, server, floating_ip.floating_ip_address)
    #print server
    delete = 'N'
    
    while delete != 'A':
        delete = raw_input('Abort (A) ?')
        
    delete_server(conn, mongo)
    delete_server(conn, client)
    delete_server(conn, server)
    
if __name__ == "__main__":
    main()
