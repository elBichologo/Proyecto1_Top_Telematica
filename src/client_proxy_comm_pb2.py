# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# NO CHECKED-IN PROTOBUF GENCODE
# source: client_proxy_comm.proto
# Protobuf Python Version: 5.27.2
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import runtime_version as _runtime_version
from google.protobuf import symbol_database as _symbol_database
from google.protobuf.internal import builder as _builder
_runtime_version.ValidateProtobufRuntimeVersion(
    _runtime_version.Domain.PUBLIC,
    5,
    27,
    2,
    '',
    'client_proxy_comm.proto'
)
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(b'\n\x17\x63lient_proxy_comm.proto\x12\x11\x63lient_proxy_comm\"\x1b\n\x0cWriteRequest\x12\x0b\n\x03log\x18\x01 \x01(\t\"\x19\n\x0bReadRequest\x12\n\n\x02id\x18\x01 \x01(\x04\"s\n\x0c\x43onfirmation\x12\x36\n\x06status\x18\x01 \x01(\x0e\x32&.client_proxy_comm.Confirmation.Status\x12\r\n\x05\x65rror\x18\x02 \x01(\t\"\x1c\n\x06Status\x12\x06\n\x02OK\x10\x00\x12\n\n\x06\x46\x41ILED\x10\x01\"\x81\x01\n\x0cReadResponse\x12\x36\n\x06status\x18\x01 \x01(\x0e\x32&.client_proxy_comm.ReadResponse.Status\x12\x0c\n\x04\x64\x61ta\x18\x02 \x01(\t\x12\r\n\x05\x65rror\x18\x03 \x01(\t\"\x1c\n\x06Status\x12\x06\n\x02OK\x10\x00\x12\n\n\x06\x46\x41ILED\x10\x01\x32\xb6\x01\n\x18\x43lientProxyCommunication\x12M\n\tWriteData\x12\x1f.client_proxy_comm.WriteRequest\x1a\x1f.client_proxy_comm.Confirmation\x12K\n\x08ReadData\x12\x1e.client_proxy_comm.ReadRequest\x1a\x1f.client_proxy_comm.ReadResponseb\x06proto3')

_globals = globals()
_builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, _globals)
_builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'client_proxy_comm_pb2', _globals)
if not _descriptor._USE_C_DESCRIPTORS:
  DESCRIPTOR._loaded_options = None
  _globals['_WRITEREQUEST']._serialized_start=46
  _globals['_WRITEREQUEST']._serialized_end=73
  _globals['_READREQUEST']._serialized_start=75
  _globals['_READREQUEST']._serialized_end=100
  _globals['_CONFIRMATION']._serialized_start=102
  _globals['_CONFIRMATION']._serialized_end=217
  _globals['_CONFIRMATION_STATUS']._serialized_start=189
  _globals['_CONFIRMATION_STATUS']._serialized_end=217
  _globals['_READRESPONSE']._serialized_start=220
  _globals['_READRESPONSE']._serialized_end=349
  _globals['_READRESPONSE_STATUS']._serialized_start=189
  _globals['_READRESPONSE_STATUS']._serialized_end=217
  _globals['_CLIENTPROXYCOMMUNICATION']._serialized_start=352
  _globals['_CLIENTPROXYCOMMUNICATION']._serialized_end=534
# @@protoc_insertion_point(module_scope)
