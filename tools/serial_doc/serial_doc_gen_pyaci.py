# Copyright (c) 2010 - 2019, Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of Nordic Semiconductor ASA nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL NORDIC SEMICONDUCTOR ASA OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import serial_doc_gen as gen
import sys
import os
import textwrap
import datetime

LICENSE_TEXT ="""# Copyright (c) 2010 - 2019, Nordic Semiconductor ASA
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
#    list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# 3. Neither the name of Nordic Semiconductor ASA nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY, AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL NORDIC SEMICONDUCTOR ASA OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE."""

CMD_HEADER = """{}

# This file was autogenerated by {} at {}.
from aci.aci_utils import CommandPacket, ResponsePacket, value_to_barray, iterable_to_barray, barray_pop
from aci.aci_evt import CmdRsp
import struct

""".format(LICENSE_TEXT,
           os.path.basename(sys.argv[0]),
           datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

EVT_HEADER = """{}

# This file was autogenerated by {} at {}.
from aci.aci_utils import EventPacket, barray_pop
import struct

""".format(LICENSE_TEXT,
           os.path.basename(sys.argv[0]),
           datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

CMD_CLASS_FMT = """class {camel_name}(CommandPacket):
    \"\"\"{description}\"\"\"
    def __init__(self{param_list}):
        __data = bytearray(){param_inits}
        super({camel_name}, self).__init__(0x{opcode:02X}, __data)


"""

CMD_RSP_CLASS_FMT = """class {camel_name}Rsp(ResponsePacket):
    \"\"\"Response to a(n) {camel_name} command.\"\"\"
    def __init__(self, raw_data):
        __data = {{}}{deserialize}
        super({camel_name}Rsp, self).__init__(\"{camel_name}\", 0x{opcode:02X}, __data)


"""


RSP_LUT_FUNCTION_FMT = """def response_deserialize(rsp):
    if not isinstance(rsp, CmdRsp):
        raise TypeError("Expected a CmdRsp object.")
    elif not rsp._data["opcode"] in RESPONSE_LUT:
        return None

    response = RESPONSE_LUT[rsp._data["opcode"]]
    # Response is always {opcode, status, [...]}
    if len(rsp._data["data"]) > 0:
        return response["object"](rsp._data["data"])
    else:
        return response["name"]


"""


EVT_CLASS_FMT = """class {camel_name}(EventPacket):
    \"\"\"{description}\"\"\"
    def __init__(self, raw_data):
        __data = {{}}{deserialize}
        super({camel_name}, self).__init__(\"{camel_name}\", 0x{opcode:02X}, __data)


"""

EVT_DESERIALIZE_FMT = """def event_deserialize(data):
    if not isinstance(data, bytearray):
        raise TypeError(\"Expected bytearray\")

    if data[1] in EVENT_LUT:
        return EVENT_LUT[data[1]](data[2:])
    else:
        return None


"""


DATA_TYPE_LUT = {
    "uint8_t"               : "B",
    "int8_t"                : "b",
    "uint16_t"              : "H",
    "int16_t"               : "h",
    "uint32_t"              : "I",
    "int32_t"               : "i",
    "dsm_handle_t"          : "H",
    "access_model_handle_t" : "H",
    "bool"                  : "?",
    1                       : "B",
    2                       : "H",
    4                       : "I"
}

def camelify(name):
    return "".join(x.title() for x in name.split(' '))


def snakeify(name):
    return name.replace(" ", "_").lower()
    # s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    # return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()


def paramify(params):
    if len(params) == 0:
        return ""
    else:
        return ", " + ", ".join(snakeify(p.name) for p in params)


def indent_wrapped_region(text, indent):
    return ("\n" + " "*indent).join(text.splitlines()).rstrip()

def description_fmt(text, params):
    INDENT = 4
    COL_MAX = 100 - 6  # Minus len("""""")

    first_period = text.find(".")
    if first_period < (COL_MAX - INDENT) and first_period < len(text)-1:
        text = text[:first_period+1] + "\n"
        text += indent_wrapped_region(textwrap.fill(text[first_period+1:], COL_MAX-INDENT),
                                      INDENT)
    else:
        text = indent_wrapped_region(textwrap.fill(text, COL_MAX - INDENT), INDENT)

    text = text.rstrip()
    COL_MAX = 100               # Reset column width

    if len(params) > 0:
        paramlist = ["\n\nParameters\n----------"]
        for param in params:
            param_fmt = "{} : {}".format(snakeify(param.name), param.typerepr())
            desc = textwrap.fill(param.description, COL_MAX - INDENT*3)
            param_fmt = " "*INDENT + param_fmt + "\n" + " "*INDENT*2 +  indent_wrapped_region(desc, INDENT*2)
            paramlist.append(param_fmt)
        text = text + indent_wrapped_region("\n".join(paramlist), INDENT)

    # Remove whitespace
    text = "\n".join([t.rstrip() for t in text.splitlines()])
    if "\n" in text:
        # Fix multi-line prettyness
        text += "\n"  + " "*INDENT
    return text


def get_variable_fmt(param):
    if param.typename in DATA_TYPE_LUT:
        return DATA_TYPE_LUT[param.typename]
    elif param.length in DATA_TYPE_LUT:
        return DATA_TYPE_LUT[param.length]
    else:
        print("Warning: Could not find conversion for variable \"%s (%d)\"" % (param.typename, param.length))
        print("         Treating as bytearray()")
        return None



def serialize_variable(outname, param):
    fmt = get_variable_fmt(param)
    if fmt:
        return "{outname} += struct.pack(\"{fmt}\", {param_name})".format(
            outname=outname, fmt="<" + fmt, param_name=snakeify(param.name))
    else:
        return "{outname} += {param_name}".format(outname=outname, param_name=snakeify(param.name))

def build_data(params):
    if len(params) == 0:
        return ""

    eol = "\n"
    ret = eol
    indent = " " * 4
    outname = "__data"
    for p in params:
        if p.array_len > 1:
            ret += indent * 2 + outname + " += iterable_to_barray({})".format(snakeify(p.name))
        else:
            ret += indent * 2 + serialize_variable(outname, p)
        ret += eol
    return ret.rstrip()


def deserialize_variable(outname, inname, index, param):
    fmt = None
    outname = outname.strip()
    inname = inname.strip()
    fmt = "<" + get_variable_fmt(param)
    return "{outname}[\"{param_name}\"], = struct.unpack(\"{fmt}\", {inname}[{begin}:{end}])".format(
        outname=outname, param_name=snakeify(param.name), inname=inname, fmt=fmt, begin=index, end=index + param.length)

def deserialize_array(outname, inname, index, param):
    if param.name.lower() == "data":
        end = ""
    else:
        end = str(index + max(param.array_len, param.length))
    return "{outname}[\"{param_name}\"] = raw_data[{begin}:{end}]".format(
        outname=outname, param_name=snakeify(param.name), inname=inname, begin=index, end=end)


def deserialize(params):
    if len(params) == 0:
        return ""

    start = " " * 8 + "__data"
    indent = " " * 4
    eol = "\n"
    index = 0
    input_name = "raw_data"
    output_name = "__data"

    ret = eol
    for p in params:
        if p.array_len > 1 or p.length > 4:
            ret += indent * 2 + deserialize_array("__data", "raw_data", index, p)
        else:
            ret += indent * 2 + deserialize_variable("__data", "raw_data", index, p)

        ret += eol
        index += p.length

    return ret.rstrip()


class AciCommand(object):
    def __init__(self, name, description, params, opcode):
        self.name = name
        self.description = description
        self.params = params
        self.opcode = opcode

    def __str__(self):
        return CMD_CLASS_FMT.format(camel_name=camelify(self.name),
                                    description=description_fmt(self.description, self.params),
                                    param_list=paramify(self.params),
                                    param_inits=build_data(self.params),
                                    opcode=self.opcode)


class AciResponse(object):
    def __init__(self, name, opcode, params):
        self.name = name
        self.opcode = opcode
        self.params = params

    def __str__(self):
        return CMD_RSP_CLASS_FMT.format(camel_name=camelify(self.name),
                                        deserialize=deserialize(self.params),
                                        opcode=self.opcode)


class AciEvent(object):
    def __init__(self, name, opcode, description, params):
        self.name = name
        self.opcode = opcode
        self.description = description
        self.params = params

    def __str__(self):
        return EVT_CLASS_FMT.format(camel_name=camelify(self.name),
                                    description=description_fmt(self.description, self.params),
                                    deserialize=deserialize(self.params),
                                    opcode=self.opcode)


class AciGenerator(gen.DocGenerator):
    def __init__(self, basename):
        super(gen.DocGenerator, self).__init__()
        self.cmd_filename = basename + "_cmd.py"
        self.evt_filename = basename + "_evt.py"

        self.commands = []
        self.responses = []
        self.events = []

    def _generate_cmds(self, parser):
        buf = CMD_HEADER

        for cmd in parser.commands:
            self.commands.append(AciCommand(cmd.raw_name,
                                            cmd.description,
                                            cmd.params,
                                            cmd.opcode))
            if cmd.response and len(cmd.response.params) > 0:
                self.responses.append(AciResponse(cmd.raw_name,
                                                  cmd.opcode,
                                                  cmd.response.params))
        for cmd in self.commands:
            buf += str(cmd)

        for rsp in self.responses:
            buf += str(rsp)

        # Make response lookup table
        buf += "RESPONSE_LUT = {\n"
        responses = ["    0x{:02X}: {{\"object\": {name}Rsp, \"name\": \"{name}\"}}".format(rsp.opcode, name=camelify(rsp.name))
                     for rsp in self.responses]
        buf += ",\n".join(responses) + "\n}\n\n\n"

        # Lookup function
        buf += RSP_LUT_FUNCTION_FMT

        buf = buf.rstrip() + "\n"
        with open(self.cmd_filename, 'w') as f:
            f.write(buf)

    def _generate_evts(self, parser):
        buf = EVT_HEADER

        for evt in parser.events:
            self.events.append(AciEvent(evt.raw_name,
                                        evt.opcode,
                                        evt.description,
                                        evt.params))

        for evt in self.events:
            buf += str(evt)

        # Make opcode enums
        buf += "class Event(object):\n"
        events = ["    {} = 0x{:02X}".format(snakeify(evt.raw_name).upper(),
                                             evt.opcode)
                  for evt in parser.events]
        buf += "\n".join(sorted(events)) + "\n\n\n"

        # Make lookup table
        buf += "EVENT_LUT = {\n"
        events = ["    Event.{}: {}".format(snakeify(evt.raw_name).upper(),
                                                  camelify(evt.raw_name))
                  for evt in parser.events]
        buf += ",\n".join(sorted(events)) + "\n}\n\n\n"

        # Make lookup function
        buf += EVT_DESERIALIZE_FMT

        buf = buf.rstrip() + "\n"
        with open(self.evt_filename, 'w') as f:
            f.write(buf)

    def generate(self, parser):
        self._generate_cmds(parser)
        self._generate_evts(parser)


if __name__ == "__main__":
    parser = gen.SerialHeaderParser()
    outdir = '.'
    try:
        outarg = sys.argv.index('-o')
        sys.argv.pop(outarg)
        outdir = sys.argv.pop(outarg)
    except:
        pass
    try:
        print("Reading desc file...")
        parser.check_desc_file('serial_desc.json')
        for filename in sys.argv[1:]:
            print("Parsing " + os.path.relpath(filename) + "...")
            parser.parse(filename)
        print("Verifying...")
        parser.verify()
        print("Generating ACI code...")
        AciGenerator(outdir + '/aci').generate(parser)
        print("Done.")
    finally:
        pass
