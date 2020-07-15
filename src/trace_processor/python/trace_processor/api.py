# Copyright (C) 2020 The Android Open Source Project
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from .http import TraceProcessorHttp


class TraceProcessor:

  # Values of these constants correspond to the QueryResponse message at
  # protos/perfetto/trace_processor/trace_processor.proto
  # Values 0 and 1 correspond to CELL_INVALID and CELL_NULL respectively,
  # which are both represented as None in this class's response
  QUERY_CELL_VARINT_FIELD_ID = 2
  QUERY_CELL_FLOAT64_FIELD_ID = 3
  QUERY_CELL_STRING_FIELD_ID = 4
  QUERY_CELL_BLOB_FIELD_ID = 5

  # This is the class returned to the user and contains one row of the
  # resultant query. Each column name is stored as an attribute of this
  # class, with the value corresponding to the column name and row in
  # the query results table.
  class Row:
    pass

  class QueryResultIterator:

    def __init__(self, column_names, batches):
      self.__cells = batches[0].cells
      self.__varint_cells = batches[0].varint_cells
      self.__float64_cells = batches[0].float64_cells
      self.__blob_cells = batches[0].blob_cells
      # TODO(aninditaghosh): Revisit string cells for larger traces
      self.__string_cells = batches[0].string_cells.split('\0')
      self.__column_names = column_names

    def get_cell_list(self, proto_index):
      if proto_index == TraceProcessor.QUERY_CELL_VARINT_FIELD_ID:
        return self.__varint_cells
      elif proto_index == TraceProcessor.QUERY_CELL_FLOAT64_FIELD_ID:
        return self.__float64_cells
      elif proto_index == TraceProcessor.QUERY_CELL_STRING_FIELD_ID:
        return self.__string_cells
      elif proto_index == TraceProcessor.QUERY_CELL_BLOB_FIELD_ID:
        return self.__blob_cells
      else:
        return None

    def __iter__(self):
      self.__next_index = 0
      return self

    def __next__(self):
      if self.__next_index >= len(self.__cells):
        raise StopIteration
      row = TraceProcessor.Row()
      for num, column_name in enumerate(self.__column_names):
        cell_list = self.get_cell_list(self.__cells[self.__next_index + num])
        if cell_list is not None:
          val = cell_list.pop(0)
        setattr(row, column_name, val or None)
      self.__next_index = self.__next_index + len(self.__column_names)
      return row

  def __init__(self, uri):
    self.http = TraceProcessorHttp(uri)

  def query(self, sql):
    response = self.http.execute_query(sql)
    return TraceProcessor.QueryResultIterator(response.column_names,
                                              response.batch)

  def metric(self, metrics):
    response = self.http.compute_metric(metrics)
    if response.error:
      raise Exception(response.error)
    return response.metrics
