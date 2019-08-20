#!/usr/bin/env python
# -*- coding: utf-8 -*-

import redcap
import os
import sys
import argparse
import logging as LOGGER
import yaml

__copyright__ = 'Copyright 2013 Vanderbilt University. All Rights Reserved'
__exe__ = os.path.basename(__file__)
__author__ = 'Karthik'
__purpose__ = "dax_manager to manage project from redcap database or \
lists of settings files"


def redcap_project_access(API_KEY):
    """
    Access point to REDCap form
    :param API_KEY:string with REDCap database API_KEY
    :return: redcap Project Object
    """
    try:
        project = redcap.Project('https://redcap.vanderbilt.edu/api/', API_KEY)
    except:
        LOGGER.error('ERROR: Could not access redcap. Either wrong API_URL/API_KEY or redcap down.')
        sys.exit(1)
    return project

def split_projects(OPTIONS):
    """

    :param OPTIONS:
    :return:
    """
    projects = OPTIONS.project.split(",")
    return projects

def check_if_complete(form_names,fields_dict):
    """

    :param form_names:
    :param fields_dict:
    :return:
    """
    for form in form_names:
        if not (fields_dict.get(str(form)+'_complete')=='2'):
            fields_dict.pop(str(form)+'_complete')
    return fields_dict

def filter_complete_forms(redcap_project,forms,projects):
    """

    :param redcap_project:
    :param forms:
    :return:
    """
    fields = []
    for form in forms:
        fields.append(str(form)+'_complete')
    records = redcap_project.export_records(records=projects,fields=fields)
    complete_field_names = []
    for record in records:
        complete_field_names.append(check_if_complete(forms,record))
    return complete_field_names

def structure_general_settings(projects_general):
    """

    :param projects_general:
    :return:
    """
    general_settings = {}
    for project in projects_general:
        general_settings.update({project.get('project_name'):project})
    return general_settings

def generate_yaml_settings_general(project_complete_forms,redcap_project):
    """

    :param complete_forms:
    :param redcap_project:
    :return:
    """
    records = []
    for forms in project_complete_forms:
        if('general_complete' in forms):
            records.append(forms.get("project_name"))
    general_data = redcap_project.export_records(records=records,forms=['general'])
    for data in general_data:
        data.pop('general_complete')
    general_dict = structure_general_settings(general_data)
    return general_dict

def generate_args_yaml_processors_modules(args_data):
    """

    :param args_data:
    :return:
    """
    args_list = args_data.split('\r\n')
    args_dict = {}
    for arg in args_list:
        args_dict.update({arg.split(":")[0]:arg.split(":")[1].strip(' ')})
    return args_dict

def split_form_names(key):
    """

    :param keys:
    :return:
    """
    process_names= ""
    module_names= ""
    if ('process_' in key):
        process_names = key.split('process_')[1].split('_complete')[0]
    elif ('module_' in key):
        module_names = key.split('module_')[1].split('_complete')[0]
    return process_names,module_names

def get_process_module_names(project_complete_forms):
    """

    :param project_complete_forms:
    :return:
    """
    project_process_modules = {}
    complete_projects = []
    for project in project_complete_forms:    #Filter for project that has settings completed other than general
        if len(project) > 2:
            project.pop('general_complete')
            complete_projects.append(project)

    for project in complete_projects:
        project_form_dict = {'project_name':project.get('project_name'),'yamlprocessors':[],'modules':[]}
        project_forms = list(project.keys())
        project_forms.remove('project_name')
        for form in project_forms:
            process_names,module_names = split_form_names(form)
            project_form_dict.get('yamlprocessors').append(process_names) if len(process_names) > 0 else process_names
            project_form_dict.get('modules').append(module_names) if len(module_names) > 0 else module_names
    project_process_modules.update({project.get('project_name'):project_form_dict})
    return project_process_modules

def get_processor_dict(yamlprocessor_names,project):
    """

    :param yaml_processor_names:
    :param project:
    :return:
    """
    processor_list = []
    for processor in yamlprocessor_names:
        processor_dict = {}
        processor_dict.update({'name': project.get(processor + '_name'),
                               'filepath': project.get(processor + '_filepath')})
        if (project.get(processor + '_args') == 1):
            processor_dict.update({'arguments':
                                       generate_args_yaml_processors_modules(project.get(processor + '_args_val'))})
        processor_list.append(processor_dict)
    return processor_list

def get_modules_dict(module_names,project):
    """

    :param module_names:
    :param project:
    :return:
    """
    module_list = []
    for module in module_names:
        module_dict = {}
        module_dict.update({'name': project.get(module + '_name'),
                           'filepath': project.get(module + '_filepath')})
        if (project.get(module + '_args')==1):
            module_dict.update({'arguments' : generate_args_yaml_processors_modules(project.get(module + '_args_val'))})
        module_list.append(module_dict)
    return module_list

def generate_yaml_settings_yaml_processors_modules(project_complete_forms,redcap_data):
    """

    :param forms:
    :param redcap_data:
    :return:
    """
    project_complete_forms_dict = get_process_module_names(project_complete_forms)
    yaml_processor_dict = {}
    for project in redcap_data:
        project_processor_module_dict = {}
        if project.get('project_name') in list(project_complete_forms_dict.keys()):
            #processor_list = []
            yamlprocessor_names = project_complete_forms_dict.get(project.get('project_name')).get('yamlprocessors')
            module_names = project_complete_forms_dict.get(project.get('project_name')).get('modules')
            if len(yamlprocessor_names) >0:
                processor_list = get_processor_dict(yamlprocessor_names,project)
                project_processor_module_dict.update({'yamlprocessors': processor_list})
            if len(module_names) > 0:
                module_list = get_modules_dict(module_names,project)
                project_processor_module_dict.update({'modules' : module_list})
        if len(project_processor_module_dict) > 0:
            yaml_processor_dict.update({project.get('project_name'): project_processor_module_dict})

    return yaml_processor_dict


def generate_yaml_settings_projects(complete_forms):
    """

    :param complete_forms:
    :return:
    """
    projects_dict = {}
    for project in complete_forms:
        yamlprocessors = {'yamlprocessors':""}
        yamlmodules = {'modules':""}
        processors = ""
        modules = ""
        processor_module_dict = {'project':project.get('project_name')}
        for form in list(project.keys()):
            process_name,module_name = split_form_names(form)
            if len(process_name) > 0:
                process_name = process_name+"_"+project.get('project_name')
                if len(yamlprocessors.get('yamlprocessors')) > 0:
                    yamlprocessors['yamlprocessors'] = yamlprocessors['yamlprocessors']+ "," +process_name
                else:
                    yamlprocessors['yamlprocessors'] = yamlprocessors['yamlprocessors']+process_name

            elif len(module_name) > 0:
                module_name = module_name+"_"+project_name
                if len(yamlmodules.get('modules')) > 0:
                    yamlmodules['modules'] = yamlmodules['modules'] + "," + module_name
                else:
                    yamlmodules['modules'] = yamlmodules['modules'] + module_name
        processor_module_dict.update(yamlprocessors)     #Need to add condition to check if yaml processors and modules aren't empty
        processor_module_dict.update(yamlmodules)
        projects_dict.update({project.get('project_name'):{"projects":[processor_module_dict]}})
    return projects_dict


def merge_and_write(projects,yaml_general_settings,yaml_processor_settings,yaml_project_settings,OPTIONS):
    """

    :param yaml_general_settings:
    :param yaml_processor_settings:
    :param yaml_project_settings:
    :return:
    """
    for project in projects:
        general = yaml_general_settings.get(project)
        processor = yaml_processor_settings.get(project)
        projects_yaml = yaml_project_settings.get(project)
        if general and processor and projects_yaml:
            yaml_file = {**general,**processor,**projects_yaml}
            filename = OPTIONS.settings_directory + project+'.yaml'
            with open(filename,'w+') as settings_file:
                yaml.dump(yaml_file,settings_file,default_flow_style=False,sort_keys=False)


def get_settings(OPTIONS):
    """

    :param OPTIONS:
    :return:
    """
    redcap_project = redcap_project_access(OPTIONS.API_KEY)
    projects = OPTIONS.project.split(',')
    redcap_data = redcap_project.export_records(records=projects)
    forms = redcap_project.forms
    complete_forms = filter_complete_forms(redcap_project,forms,projects)
    yaml_general_settings = generate_yaml_settings_general(complete_forms,redcap_project)
    yaml_processor_settings= generate_yaml_settings_yaml_processors_modules(complete_forms,redcap_data)
    yaml_project_settings = generate_yaml_settings_projects(complete_forms)
    #yaml_project_settings = generate_yaml_settings_projects(complete_forms,redcap_project)
    merge_and_write(projects,yaml_general_settings,yaml_processor_settings,yaml_project_settings,OPTIONS)


def add_to_parser():
    """
    Add arguments to default parser
    :return: parser object
    """
    parser = argparse.ArgumentParser(description='DAX Manager')
    parser.add_argument("-k","--key",dest='API_KEY',default=None, \
                        required=True, help='API Key to database')
    parser.add_argument("-p","--project",dest='project',default=None, \
                        required=True, help='Project Name')
    parser.add_argument("-s","--settings",dest='settings_directory',default=None,\
                        help='project_settings_directory')
    parser.add_argument("-l","--log_file",dest='logfile',default=None,\
                         help='path to log file')
    parser.add_argument("--write",dest='write',action='store_true',\
                        help='write settings from REDCap')
    return parser


if __name__ == '__main__':
    parser = add_to_parser()
    OPTIONS = parser.parse_args()
    if(OPTIONS.logfile is None): # this part needs reconsideration.
        LOGGER.basicConfig(level=LOGGER.DEBUG,
                           format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                           datefmt='%Y-%m-%d %H:%M:%S')
    else:
        LOGGER.basicConfig(filename=OPTIONS.logfile, level=LOGGER.DEBUG,
                           format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                           datefmt='%Y-%m-%d %H:%M:%S')
    console = LOGGER.StreamHandler()
    console.setLevel(LOGGER.INFO)
    get_settings(OPTIONS)
