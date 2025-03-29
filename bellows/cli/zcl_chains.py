#!/usr/bin/env -S python
'''
ZCL Chains - create chains of zcl commands
'''
import asyncio
import logging
import math
import re

import click
import click_log

from bellows.cli import InterprocessObjects
from bellows.cli import util

import zigpy.exceptions

LOGGER = logging.getLogger(__name__)

class Link():
    '''
    Link - piece of a chain
    '''
    def __init__(self, name, function, parameters):
        '''
        constructor of a link object
        '''
        self.name = name
        self.function = function
        self.parameters = parameters
        self.next = None

class Chain():
    '''
    Chain - strand of links
    '''
    class ParameterMismatch(Exception):
        '''
        Parameter lists do not match in length
        '''
        def __init__(self, message):
            '''
            Exception constructor
            '''
            super().__init__(message)
            self.message = message

        def __str__(self):
            '''
            Error message to return
            '''
            return self.message

    class Store(Exception):
        '''
        Parameter Store error
        '''
        def __init__(self, message):
            '''
            Exception constructor
            '''
            super().__init__(message)
            self.message = message

        def __str__(self):
            '''
            Error message to return
            '''
            return self.message

    class ParameterError(Exception):
        '''
        Parameter error
        '''
        def __init__(self, message):
            '''
            Exception constructor
            '''
            super().__init__(message)
            self.message = message

        def __str__(self):
            '''
            Error message to return
            '''
            return self.message

    def __init__(self, link, name, device, ipo):
        '''
        constructor of a link object
        '''
        self.head = link
        self.name = name
        self.device = device
        self.ipo = ipo
        self.results = None
    def add(self, link):
        '''
        add a link to a chain
        '''
        this_link = self.head
        while this_link.next is not None:
            this_link = this_link.next
        this_link.next = link
    def print_chain(self):
        '''
        print the existing chain
        '''
        this_link = self.head
        print(f"This chain, {self.name}, has links:")
        while this_link is not None:
            print(this_link.name)
            this_link = this_link.next
        print()

    async def execute(self, results_array=None):
        '''
        execute the chain of commands
        '''
        if results_array is not None:
            self.results = results_array
        this_link = self.head
        v = None
        while this_link is not None:
            LOGGER.debug(type(this_link.function))
            last_link = None
            try:
                LOGGER.debug(f"processing {this_link.name}")
                LOGGER.debug(f"this_link.parameters: {this_link.parameters},"
                             " type: {type(this_link.parameters)}")
                p = eval(this_link.parameters),
                if p[0] is None:
                    v = await this_link.function()
                else:
                    if isinstance(p[0], tuple):
                        p = p[0]
                        new_p = []
                        for index,_ in enumerate(p):
                            if isinstance(p[index], str):
                                new_p.append(int(self.ipo.lastStatus[self.device+p[index]]))
                            else:
                                new_p.append(p[index])
                        p = tuple(new_p)
                    LOGGER.debug(f"this_link.parameters: {this_link.parameters}, p: {p},"
                                 " type(p): {type(p)}")
                    v = await this_link.function(*p)
                LOGGER.debug(f"after {this_link.name}, results array is: {self.results}")
                LOGGER.debug(f"and lastStatus is: {self.ipo.lastStatus}")
                LOGGER.debug(f"and v is: {v}")
                last_link = this_link
                this_link = this_link.next
            except (zigpy.exceptions.ZigbeeException, ZeroDivisionError) as e:
                LOGGER.debug(f"exception while processing a chain: {e}")
                if 'on' in this_link.name or 'off' in this_link.name or 'status' in this_link.name:
                    self.ipo.update_status.send((self.device, "", 'unknown'))
                elif 'read' in this_link.name:  # set all values to zero - typically invalid
                    full_name = self.name
                    if self.device not in full_name:
                        full_name = self.device+self.name
                    labels = self.ipo.status_labels[full_name]
                    indices = self.ipo.result_indices[full_name]
                    LOGGER.debug(f"labels: {labels}")
                    for index,_ in enumerate(labels):
                        label = labels[index]
                        if label == '""':
                            label = ''
                        self.ipo.update_status.send((self.device, label, 0))
                last_link = None
                break
        if last_link is not None and last_link.name != 'store':
            full_name = self.name
            if self.device not in full_name:
                full_name = self.device+self.name
            labels = self.ipo.status_labels[full_name]
            indices = self.ipo.result_indices[full_name]
            LOGGER.debug(f"labels: {labels}")
            for index,_ in enumerate(labels):
                label = labels[index]
                if label == '""':
                    label = ''
                v_index = indices[index]
                if self.results is None:
                    index_string = "v" + v_index
                else:
                    LOGGER.debug(f"results: {self.results}")
                    index_string = "self.results"+v_index
                LOGGER.debug(f"index string: {index_string}")
                x = eval(index_string)
                LOGGER.debug(f"result indices: index_string: {x}")
                if 'on' in last_link.name or 'off' in last_link.name or 'status' in last_link.name:
                    if x == 0:
                        value = 'off'
                    else:
                        value = 'on'
                    self.ipo.update_status.send((self.device, label, value))
                else:
                    self.ipo.update_status.send((self.device, label, x))

    async def setp(self, list_of_constants):
        '''
        setp - set parameters
        '''
        self.results = list_of_constants

    async def addp(self, list_of_constants):
        '''
        addp - add to existing parameters
        '''
        if len(self.results) == len(list_of_constants):
            for index,_ in enumerate(self.results):
                if isinstance(list_of_constants[index], str):
                    self.results[index] += self.ipo.lastStatus[self.device+list_of_constants[index]]
                else:
                    self.results[index] += list_of_constants[index]
                self.results[index] = math.floor(self.results[index] + 0.5)
        else:
            raise Chain.ParameterMismatch("addp attempting to use inconsistent parameter lists")

    async def subtractp(self, list_of_constants):
        '''
        subtractp - subtract from existing parameters
        '''
        if len(self.results) == len(list_of_constants):
            for index,_ in enumerate(self.results):
                if isinstance(list_of_constants[index], str):
                    self.results[index] -= self.ipo.lastStatus[self.device+list_of_constants[index]]
                else:
                    self.results[index] -= list_of_constants[index]
                self.results[index] = math.floor(self.results[index] + 0.5)
        else:
            raise Chain.ParameterMismatch("subtractp attempting to use inconsistent parameter"
                                          " lists")

    async def multiplyp(self, list_of_constants):
        '''
        multiplyp - multiply existing parameters by list
        '''
        if len(self.results) == len(list_of_constants):
            for index,_ in enumerate(self.results):
                if isinstance(list_of_constants[index], str):
                    self.results[index] *= self.ipo.lastStatus[self.device+list_of_constants[index]]
                else:
                    self.results[index] *= list_of_constants[index]
                self.results[index] = math.floor(self.results[index] + 0.5)
        else:
            raise Chain.ParameterMismatch("multiplyp attempting to use inconsistent parameter"
                                          " lists")

    async def dividep(self, list_of_constants):
        '''
        dividep - divide into existing parameters by list
        '''
        if len(self.results) == len(list_of_constants):
            for index,_ in enumerate(self.results):
                if isinstance(list_of_constants[index], str):
                    self.results[index] /= self.ipo.lastStatus[self.device+list_of_constants[index]]
                else:
                    self.results[index] /= list_of_constants[index]
                self.results[index] = math.floor(self.results[index] + 0.5)
        else:
            raise Chain.ParameterMismatch("dividep attempting to use inconsistent parameter lists")

    async def store(self, arr):
        '''
        store results[index] at name
        '''
        if len(arr) == 2:
            index = arr[0]
            name = arr[1]
        else:
            raise Chain.ParameterError("store given invalid parameter list")
        if 0 <= index < len(self.results):
            self.ipo.lastStatus[self.device+name] = self.results[index]
        else:
            raise Chain.Store(f"index, {index} is not valid for results array {len(self.results)}")

    async def read(self, arr):
        '''
        read from store at location name and put it into results at index
        '''
        if len(arr) == 2:
            name = arr[0]
            index = arr[1]
        else:
            raise Chain.ParameterError("store given invalid parameter list")
        if 0 <= index < len(self.results):
            if self.device+name in self.ipo.lastStatus:
                self.results[index] = self.ipo.lastStatus[self.device+name]
            else:
                raise Chain.Store(f"{self.device+name} is not in last status store")
        else:
            raise Chain.Store(f"index, {index} is not valid for results array {len(self.results)}")

def get_address(command):
    '''
    Get the address from a command
    '''
    result = command.replace('on', '')
    result = result.replace('off', '')
    result = result.replace('status', '')
    result = result.replace('readCT', '')
    result = result.replace('readLevel', '')
    result = result.replace('setCT', '')
    result = result.replace('setLevel', '')
    result = result.split(' ')[0]
    return result

class ZCL_Chains():
    '''
    ZCL chains
    '''
    def __init__(self, command_list):
        '''
        ZCL chains constructor
        '''
        self.debug = logging.DEBUG == LOGGER.getEffectiveLevel()
        print(f"************** DEBUG ******* {self.debug}")
        self.command_list = command_list
        self.ipo = InterprocessObjects.InterprocessObjects()
        self.chain_set = {}
        LOGGER.debug(self.ipo.commandList)
        LOGGER.debug(self.ipo.command_tuples)
        for command in command_list:
            device = get_address(command)
            chain_name = command
            link = Link(chain_name, command_list[command], self.ipo.command_tuples[command])
            chain = Chain(link, chain_name, device, self.ipo)
            self.chain_set[chain_name] = chain
        derived_chain_set = {}
        pattern = re.compile(r'(\(.*?\))')
        for device in self.ipo.network_devices:
            with open("derived_chains.txt", "r", encoding="utf-8") as dc:
                LOGGER.debug(f"building derived chains for {device}")
                chain_name = ""
                chain = None
                for line in dc:
                    line = line.strip()
                    if line[0] == '#':
                        continue
                    fields = re.split(r', *',line)
                    if chain_name != fields[0]:   # a new chain, store old one
                        if chain_name != "":
                            derived_chain_set[device+chain_name] = chain
                        chain_name = fields[0]
                        chain = None
                    link_name = fields[1]
                    if hasattr(Chain, link_name):
                        func = eval("Chain."+link_name)
                        parameters = re.findall(pattern, line)
                        if len(parameters) == 3:
                            link = Link(link_name, func, parameters[0])
                        else:
                            LOGGER.warning("something is wrong in the configuration file:({line})")
                    else:
                        parameters = re.findall(pattern, line)
                        if len(parameters) == 3:
                            if device+link_name in self.chain_set:
                                link = Link(link_name, command_list[device+link_name],
                                            parameters[0])
                                if '(None)' not in parameters[1]:
                                    self.ipo.status_labels[device+link_name] = (
                                        re.split(r', *', parameters[1].replace(
                                            '(','').replace(')','')))
                                if '(None)' not in parameters[2]:
                                    self.ipo.result_indices[device+link_name] = (
                                        re.split(r', *', parameters[2].replace(
                                            '(','').replace(')','')))
                            else:
                                LOGGER.warning(f"{chain_name} with link {link_name} is not"
                                               " supported by device {device}")
                                if self.debug:
                                    self.print()
                                chain = None
                                continue # this command is not supported with this device
                        else:
                            LOGGER.warning("something is wrong in the configuration file:({line}}")
                    if chain is None:
                        chain = Chain(link, chain_name, device, self.ipo)
                    else:
                        chain.add(link)
                if chain is not None:
                    derived_chain_set[device+chain_name] = chain
        for key, value in derived_chain_set.items():
            self.chain_set[key] = value
        if self.debug:
            self.print()

    def print(self):
        '''
        Print the entire ZCL chain set
        '''
        print("Chain set contains:")
        for key, value in self.chain_set.items():
            print(f"This chain, {key}, has links:")
            this_link = value.head
            while this_link is not None:
                print(this_link.name)
                this_link = this_link.next
            print()

    async def execute(self, command, parameters=None):
        '''
        Execute a ZCL chain
        '''
        if parameters is None:
            await self.chain_set[command].execute()
        else:
            await self.chain_set[command].execute([parameters])

@click.command()
@click_log.simple_verbosity_option(logging.getLogger(), default='INFO')
@util.background
async def main():
    '''
    main/test only program
    '''
    logging.basicConfig(format='%(asctime)s %(levelname)-8s [%(filename)s:%(lineno)4d] %(message)s',
                        datefmt=' %Y-%m-%d:%H:%M:%S', level=LOGGER.getEffectiveLevel())
    ipo = InterprocessObjects.InterprocessObjects()
    ipo.lastStatus = {}
    ipo.status_labels = {}
    ipo.result_indices = {}
    ipo.lastStatus["b0:c7:de:ff:fe:52:ca:58"] = 'on'
    ipo.lastStatus["b0:c7:de:ff:fe:52:ca:58minMireds"] = 153
    ipo.lastStatus["b0:c7:de:ff:fe:52:ca:58maxMireds"] = 555
    ipo.lastStatus["b0:c7:de:ff:fe:52:ca:58CT"] = 285
    ipo.status_labels["color temperature"] = ['colorT']
    ipo.result_indices["color temperature"] = ['[0]']
    print(f"after initialization, lastStatus is: {ipo.lastStatus}")
    chain_one = {}
    chain_one = Chain(Link('store', Chain.store, "(self, [0, 'working'])"), 'color temperature',
                      'b0:c7:de:ff:fe:52:ca:58', ipo)
    chain_one.add(Link('setp', Chain.setp, "(self, [1000000])"))
    chain_one.add(Link('dividep', Chain.dividep, "(self, ['working'])"))
    chain_one.add(Link('store', Chain.store, "(self, [0, 'CT'])"))
    chain_one.print_chain()
    try:
        await chain_one.execute([5000])
    except Chain.ParameterMismatch as e:
        print(f"Exception received: {e}")
    print(f"after execution of the chain, lastStatus is: {ipo.lastStatus}")
if __name__ == "__main__":
    asyncio.run(main())
