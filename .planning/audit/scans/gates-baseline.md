# 扫描档案:现有门禁基线(仓内直调)

**Created:** 2026-07-05
**基线:** `5927f36`(全 SHA 见 `.planning/audit/CHARTER.md` 审计基线章节)

per D-05(现有门禁)/ D-07(命令+版本+输出存档)/ D-08(不经 make,仓内直调实体命令)。三条门禁均为只读命令,在仓库工作树内直调(mypy 需项目依赖环境、miniprogram_lint 是仓内模块,无法对导出副本运行——Pitfall 6);直调前后各跑一次零 diff 快查并记录于本档案(见下),保证门禁运行时段内工作树 == 基线。venv 经 `UV_PROJECT_ENVIRONMENT` 指向 scratchpad(仓库外),`uv run --frozen` 防 lock 更新,零仓库写入。命中 ≠ 发现:销号列 03-02 填。

**工具版本:** uv 0.8.14 / mypy 2.1.0 (compiled) / ruff 0.15.20 / Python 3.12.11(venv 解释器)/ miniprogram_lint 仓内模块(基线 218 行)

## 直调前零 diff 快查(Pitfall 6)

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——PASS
```

## 门禁 1:mypy(strict,范围见根 pyproject.toml)

```bash
uv run mypy   # 直调,不经 make;实跑加 --frozen 防 lock 更新
```

**结果:exit=1,1 error / 67 files checked**

```
apps/fc/shared/app.py:14: error: Cannot find implementation or library stub for module named "handler"  [import-not-found]
apps/fc/shared/app.py:14: note: See https://mypy.readthedocs.io/en/stable/running_mypy.html#missing-imports
Found 1 error in 1 file (checked 67 source files)
```

**注记(待 03-02 销号核实):** `app.py` 的 `import handler` 是 FC 自定义运行时的部署态导入(`fc_shared` 与函数目录 vendored 同层,handler.py 仅在部署 zip 内与 app.py 同目录)——门禁在仓内直调是否必然报此错、Makefile `typecheck` 目标实态如何,属 TOOL 维度观察点,此处只存档不判断。

## 门禁 2:ruff check(门禁规则集 E,F,I,UP,B,配置在根 pyproject.toml)

```bash
uv run ruff check   # 直调,不经 make;实跑加 --frozen 防 lock 更新
```

**结果:exit=1,Found 89 errors(43 fixable)**。命中文件分布注记:全部 89 条落在 `docs/example/start-fc-main/`(vendored 外部仓库,80 条)、`scripts/test_asr.py`(6 条)、`scripts/ralph/`(3 条),80 + 6 + 3 = 89 ✓——被审三层主体代码(apps/)零命中;裸跑 `ruff check` 无路径参数时扫描范围覆盖 CHARTER 扫描排除清单内目录,该现象本身是 TOOL 维度观察点(Makefile lint 目标的实际调用口径待 03-06 静读核对),此处只存档不判断。

**完整输出:**

```
UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/async-task/python3/src/code/async-task/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 | import logging
3 | import time
  |
help: Remove unnecessary coding comment

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/async-task/python3/src/code/async-task/index.py:2:1
  |
1 |   # -*- coding: utf-8 -*-
2 | / import logging
3 | | import time
4 | | import json
  | |___________^
5 |
6 |   # To enable the initializer feature (https://help.aliyun.com/document_detail/158208.html)
  |
help: Organize imports

UP032 [*] Use f-string instead of `format` call
  --> docs/example/start-fc-main/async-task/python3/src/code/async-task/index.py:15:17
   |
13 | def handler(event, context):
14 |     logger = logging.getLogger()
15 |     logger.info('async task begin with event: {}'.format(event))
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
16 |
17 |     evt = json.loads(event)
   |
help: Convert to f-string

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/async-task/python3/src/code/dest-fail/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 | import logging
  |
help: Remove unnecessary coding comment

UP032 [*] Use f-string instead of `format` call
  --> docs/example/start-fc-main/async-task/python3/src/code/dest-fail/index.py:13:17
   |
11 | def handler(event, context):
12 |     logger = logging.getLogger()
13 |     logger.info('destnation fail: {}'.format(event))
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
14 |     return {}
   |
help: Convert to f-string

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/async-task/python3/src/code/dest-succ/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 | import logging
  |
help: Remove unnecessary coding comment

UP032 [*] Use f-string instead of `format` call
  --> docs/example/start-fc-main/async-task/python3/src/code/dest-succ/index.py:13:17
   |
11 | def handler(event, context):
12 |     logger = logging.getLogger()
13 |     logger.info('destnation success: {}'.format(event))
   |                 ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
14 |     return {}
   |
help: Convert to f-string

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:1:1
  |
1 | / import logging
2 | | import sys
3 | | import traceback
4 | | from flask import Flask, request
  | |________________________________^
5 |   app = Flask(__name__)
  |
help: Organize imports

E501 Line too long (106 > 100)
  --> docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:56:101
   |
55 |     print("FC Invoke End RequestId: " + request_id)
56 |     return "Hello from FC event function, your input: " + event_str + ", request_id: " + request_id + "\n"
   |                                                                                                     ^^^^^^
   |

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-container-function/fc-custom-container-no-web-server-event-fibonacci/app.py:1:1
  |
1 | / import os
2 | | import numpy as np
  | |__________________^
3 |
4 |   def PrintFibonacci(first, second, length):
  |
help: Organize imports

F401 [*] `os` imported but unused
 --> docs/example/start-fc-main/custom-container-function/fc-custom-container-no-web-server-event-fibonacci/app.py:1:8
  |
1 | import os
  |        ^^
2 | import numpy as np
  |
help: Remove unused import: `os`

F401 [*] `numpy` imported but unused
 --> docs/example/start-fc-main/custom-container-function/fc-custom-container-no-web-server-event-fibonacci/app.py:2:17
  |
1 | import os
2 | import numpy as np
  |                 ^^
3 |
4 | def PrintFibonacci(first, second, length):
  |
help: Remove unused import: `numpy`

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-container-function/fc-custom-container-websocket-python3.9/src/code/app.py:1:1
  |
1 | / import asyncio
2 | | import websockets
  | |_________________^
3 |
4 |   async def echo(websocket, path):
  |
help: Organize imports

UP015 [*] Unnecessary mode argument
  --> docs/example/start-fc-main/custom-function/f#/fc-custom-fsharp-http/src/init_helper.py:8:25
   |
 6 | d = {}
 7 | for filename in filenames:
 8 |     with open(filename, "r") as f:
   |                         ^^^
 9 |         pop_data = json.load(f)
10 |         pop_data["urls"] = "http://*:9000"
   |
help: Remove mode argument

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-event/src/code/server.py:1:1
  |
1 | / from flask.logging import default_handler
2 | | import time
3 | | from flask import Flask
4 | | from flask import request
5 | | import json
6 | | import sys
7 | | import traceback
8 | | import logging
  | |______________^
  |
help: Organize imports

F401 [*] `flask.logging.default_handler` imported but unused
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-event/src/code/server.py:1:27
  |
1 | from flask.logging import default_handler
  |                           ^^^^^^^^^^^^^^^
2 | import time
3 | from flask import Flask
  |
help: Remove unused import: `flask.logging.default_handler`

F401 [*] `time` imported but unused
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-event/src/code/server.py:2:8
  |
1 | from flask.logging import default_handler
2 | import time
  |        ^^^^
3 | from flask import Flask
4 | from flask import request
  |
help: Remove unused import: `time`

UP010 [*] Unnecessary `__future__` import `print_function` for target Python version
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:3:1
  |
1 | """The Python implementation of the GRPC helloworld.Greeter client."""
2 |
3 | from __future__ import print_function
  | ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
4 |
5 | import logging
  |
help: Remove unnecessary `__future__` import

I001 [*] Import block is un-sorted or un-formatted
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:3:1
   |
 1 |   """The Python implementation of the GRPC helloworld.Greeter client."""
 2 |
 3 | / from __future__ import print_function
 4 | |
 5 | | import logging
 6 | | import random
 7 | | import argparse
 8 | |
 9 | | import grpc
10 | | import helloworld_pb2
11 | | import helloworld_pb2_grpc
12 | | import helloworld_resources
   | |___________________________^
13 |
14 |   parser = argparse.ArgumentParser(description="grpc params")
   |
help: Organize imports

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:40:15
   |
39 |     for feature in features:
40 |         print("Feature called %s at %s" % (feature.name, feature.location))
   |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:46:15
   |
44 |     for _ in range(0, 10):
45 |         random_feature = feature_list[random.randint(0, len(feature_list) - 1)]
46 |         print("Visiting point %s" % random_feature.location)
   |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
47 |         yield random_feature.location
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:55:11
   |
53 |     route_iterator = generate_route(feature_list)
54 |     route_summary = stub.RecordRoute(route_iterator)
55 |     print("Finished trip with %s points " % route_summary.point_count)
   |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
56 |     print("Passed %s features " % route_summary.feature_count)
57 |     print("Travelled %s meters " % route_summary.distance)
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:56:11
   |
54 |     route_summary = stub.RecordRoute(route_iterator)
55 |     print("Finished trip with %s points " % route_summary.point_count)
56 |     print("Passed %s features " % route_summary.feature_count)
   |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
57 |     print("Travelled %s meters " % route_summary.distance)
58 |     print("It took %s seconds " % route_summary.elapsed_time)
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:57:11
   |
55 |     print("Finished trip with %s points " % route_summary.point_count)
56 |     print("Passed %s features " % route_summary.feature_count)
57 |     print("Travelled %s meters " % route_summary.distance)
   |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
58 |     print("It took %s seconds " % route_summary.elapsed_time)
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:58:11
   |
56 |     print("Passed %s features " % route_summary.feature_count)
57 |     print("Travelled %s meters " % route_summary.distance)
58 |     print("It took %s seconds " % route_summary.elapsed_time)
   |           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:70:15
   |
68 |     ]
69 |     for msg in messages:
70 |         print("Sending %s at %s" % (msg.message, msg.location))
   |               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
71 |         yield msg
   |
help: Replace with format specifiers

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:77:15
   |
75 |       responses = stub.RouteChat(generate_messages())
76 |       for response in responses:
77 |           print("Received message %s at %s" %
   |  _______________^
78 | |               (response.message, response.location))
   | |___________________________________________________^
   |
help: Replace with format specifiers

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_server.py:1:1
  |
1 | / from concurrent import futures
2 | | import logging
3 | | import math
4 | | import time
5 | |
6 | | import grpc
7 | | import helloworld_pb2
8 | | import helloworld_pb2_grpc
9 | | import helloworld_resources
  | |___________________________^
  |
help: Organize imports

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_server.py:48:50
   |
47 |     def SayHello(self, request, context):
48 |         return helloworld_pb2.HelloReply(message='Hello, %s!' % request.name)
   |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^
49 |
50 |     def ListFeatures(self, request, context):
   |
help: Replace with format specifiers

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 | # Generated by the protocol buffer compiler.  DO NOT EDIT!
3 | # source: helloworld.proto
  |
help: Remove unnecessary coding comment

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:5:1
  |
3 |   # source: helloworld.proto
4 |   """Generated protocol buffer code."""
5 | / from google.protobuf.internal import builder as _builder
6 | | from google.protobuf import descriptor as _descriptor
7 | | from google.protobuf import descriptor_pool as _descriptor_pool
8 | | from google.protobuf import symbol_database as _symbol_database
  | |_______________________________________________________________^
9 |   # @@protoc_insertion_point(imports)
  |
help: Organize imports

E501 Line too long (1379 > 100)
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:16:101
   |
16 | …rld\"\x1c\n\x0cHelloRequest\x12\x0c\n\x04name\x18\x01 \x01(\t\"\x1d\n\nHelloReply\x12\x0f\n\x07message\x18\x01 \x01(\t\",\n\x05Point\x12\x10\n\x08latitude\x18\x01 \x01(\x05\x12\x11\n\tlongitude\x18\x02 \x01(\x05\"I\n\tRectangle\x12\x1d\n\x02lo\x18\x01 \x01(\x0b\x32\x11.helloworld.Point\x12\x1d\n\x02hi\x18\x02 \x01(\x0b\x32\x11.helloworld.Point\"<\n\x07\x46\x65\x61ture\x12\x0c\n\x04name\x18\x01 \x01(\t\x12#\n\x08location\x18\x02 \x01(\x0b\x32\x11.helloworld.Point\"A\n\tRouteNote\x12#\n\x08location\x18\x01 \x01(\x0b\x32\x11.helloworld.Point\x12\x0f\n\x07message\x18\x02 \x01(\t\"b\n\x0cRouteSummary\x12\x13\n\x0bpoint_count\x18\x01 \x01(\x05\x12\x15\n\rfeature_count\x18\x02 \x01(\x05\x12\x10\n\x08\x64istance\x18\x03 \x01(\x05\x12\x14\n\x0c\x65lapsed_time\x18\x04 \x01(\x05\x32\x8a\x02\n\x07Greeter\x12>\n\x08SayHello\x12\x18.helloworld.HelloRequest\x1a\x16.helloworld.HelloReply\"\x00\x12>\n\x0cListFeatures\x12\x15.helloworld.Rectangle\x1a\x13.helloworld.Feature\"\x00\x30\x01\x12>\n\x0bRecordRoute\x12\x11.helloworld.Point\x1a\x18.helloworld.RouteSummary\"\x00(\x01\x12?\n\tRouteChat\x12\x15.helloworld.RouteNote\x1a\x15.helloworld.RouteNote\"\x00(\x01\x30\x01\x42X\n\x16io.grpc.examples.protoB\x0fHelloWorldProtoP\x01Z+google.golang.org/grpc/examples/proto/protob\x06proto3')
   |       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
17 | …
18 | …
   |

E712 Avoid equality comparisons to `False`; use `not _descriptor._USE_C_DESCRIPTORS:` for false checks
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:20:4
   |
18 | _builder.BuildMessageAndEnumDescriptors(DESCRIPTOR, globals())
19 | _builder.BuildTopDescriptorsAndMessages(DESCRIPTOR, 'helloworld_pb2', globals())
20 | if _descriptor._USE_C_DESCRIPTORS == False:
   |    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
21 |
22 |   DESCRIPTOR._options = None
   |
help: Replace with `not _descriptor._USE_C_DESCRIPTORS`

E501 Line too long (136 > 100)
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:23:101
   |
22 | …
23 | …xamples.protoB\017HelloWorldProtoP\001Z+google.golang.org/grpc/examples/proto/proto'
   |                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
24 | …
25 | …
   |

F821 Undefined name `_HELLOREQUEST`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:24:3
   |
22 |   DESCRIPTOR._options = None
23 |   DESCRIPTOR._serialized_options = b'\n\026io.grpc.examples.protoB\017HelloWorldProtoP\001Z+google.golang.org/grpc/examples/proto/prot…
24 |   _HELLOREQUEST._serialized_start=32
   |   ^^^^^^^^^^^^^
25 |   _HELLOREQUEST._serialized_end=60
26 |   _HELLOREPLY._serialized_start=62
   |

F821 Undefined name `_HELLOREQUEST`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:25:3
   |
23 |   DESCRIPTOR._serialized_options = b'\n\026io.grpc.examples.protoB\017HelloWorldProtoP\001Z+google.golang.org/grpc/examples/proto/prot…
24 |   _HELLOREQUEST._serialized_start=32
25 |   _HELLOREQUEST._serialized_end=60
   |   ^^^^^^^^^^^^^
26 |   _HELLOREPLY._serialized_start=62
27 |   _HELLOREPLY._serialized_end=91
   |

F821 Undefined name `_HELLOREPLY`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:26:3
   |
24 |   _HELLOREQUEST._serialized_start=32
25 |   _HELLOREQUEST._serialized_end=60
26 |   _HELLOREPLY._serialized_start=62
   |   ^^^^^^^^^^^
27 |   _HELLOREPLY._serialized_end=91
28 |   _POINT._serialized_start=93
   |

F821 Undefined name `_HELLOREPLY`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:27:3
   |
25 |   _HELLOREQUEST._serialized_end=60
26 |   _HELLOREPLY._serialized_start=62
27 |   _HELLOREPLY._serialized_end=91
   |   ^^^^^^^^^^^
28 |   _POINT._serialized_start=93
29 |   _POINT._serialized_end=137
   |

F821 Undefined name `_POINT`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:28:3
   |
26 |   _HELLOREPLY._serialized_start=62
27 |   _HELLOREPLY._serialized_end=91
28 |   _POINT._serialized_start=93
   |   ^^^^^^
29 |   _POINT._serialized_end=137
30 |   _RECTANGLE._serialized_start=139
   |

F821 Undefined name `_POINT`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:29:3
   |
27 |   _HELLOREPLY._serialized_end=91
28 |   _POINT._serialized_start=93
29 |   _POINT._serialized_end=137
   |   ^^^^^^
30 |   _RECTANGLE._serialized_start=139
31 |   _RECTANGLE._serialized_end=212
   |

F821 Undefined name `_RECTANGLE`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:30:3
   |
28 |   _POINT._serialized_start=93
29 |   _POINT._serialized_end=137
30 |   _RECTANGLE._serialized_start=139
   |   ^^^^^^^^^^
31 |   _RECTANGLE._serialized_end=212
32 |   _FEATURE._serialized_start=214
   |

F821 Undefined name `_RECTANGLE`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:31:3
   |
29 |   _POINT._serialized_end=137
30 |   _RECTANGLE._serialized_start=139
31 |   _RECTANGLE._serialized_end=212
   |   ^^^^^^^^^^
32 |   _FEATURE._serialized_start=214
33 |   _FEATURE._serialized_end=274
   |

F821 Undefined name `_FEATURE`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:32:3
   |
30 |   _RECTANGLE._serialized_start=139
31 |   _RECTANGLE._serialized_end=212
32 |   _FEATURE._serialized_start=214
   |   ^^^^^^^^
33 |   _FEATURE._serialized_end=274
34 |   _ROUTENOTE._serialized_start=276
   |

F821 Undefined name `_FEATURE`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:33:3
   |
31 |   _RECTANGLE._serialized_end=212
32 |   _FEATURE._serialized_start=214
33 |   _FEATURE._serialized_end=274
   |   ^^^^^^^^
34 |   _ROUTENOTE._serialized_start=276
35 |   _ROUTENOTE._serialized_end=341
   |

F821 Undefined name `_ROUTENOTE`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:34:3
   |
32 |   _FEATURE._serialized_start=214
33 |   _FEATURE._serialized_end=274
34 |   _ROUTENOTE._serialized_start=276
   |   ^^^^^^^^^^
35 |   _ROUTENOTE._serialized_end=341
36 |   _ROUTESUMMARY._serialized_start=343
   |

F821 Undefined name `_ROUTENOTE`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:35:3
   |
33 |   _FEATURE._serialized_end=274
34 |   _ROUTENOTE._serialized_start=276
35 |   _ROUTENOTE._serialized_end=341
   |   ^^^^^^^^^^
36 |   _ROUTESUMMARY._serialized_start=343
37 |   _ROUTESUMMARY._serialized_end=441
   |

F821 Undefined name `_ROUTESUMMARY`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:36:3
   |
34 |   _ROUTENOTE._serialized_start=276
35 |   _ROUTENOTE._serialized_end=341
36 |   _ROUTESUMMARY._serialized_start=343
   |   ^^^^^^^^^^^^^
37 |   _ROUTESUMMARY._serialized_end=441
38 |   _GREETER._serialized_start=444
   |

F821 Undefined name `_ROUTESUMMARY`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:37:3
   |
35 |   _ROUTENOTE._serialized_end=341
36 |   _ROUTESUMMARY._serialized_start=343
37 |   _ROUTESUMMARY._serialized_end=441
   |   ^^^^^^^^^^^^^
38 |   _GREETER._serialized_start=444
39 |   _GREETER._serialized_end=710
   |

F821 Undefined name `_GREETER`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:38:3
   |
36 |   _ROUTESUMMARY._serialized_start=343
37 |   _ROUTESUMMARY._serialized_end=441
38 |   _GREETER._serialized_start=444
   |   ^^^^^^^^
39 |   _GREETER._serialized_end=710
40 | # @@protoc_insertion_point(module_scope)
   |

F821 Undefined name `_GREETER`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:39:3
   |
37 |   _ROUTESUMMARY._serialized_end=441
38 |   _GREETER._serialized_start=444
39 |   _GREETER._serialized_end=710
   |   ^^^^^^^^
40 | # @@protoc_insertion_point(module_scope)
   |

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:3:1
  |
1 |   # Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
2 |   """Client and server classes corresponding to protobuf-defined services."""
3 | / import grpc
4 | |
5 | | import helloworld_pb2 as helloworld__pb2
  | |________________________________________^
  |
help: Organize imports

UP004 [*] Class `GreeterStub` inherits from `object`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:8:19
   |
 8 | class GreeterStub(object):
   |                   ^^^^^^
 9 |     """The greeting service definition.
10 |     """
   |
help: Remove `object` inheritance

UP004 [*] Class `GreeterServicer` inherits from `object`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:40:23
   |
40 | class GreeterServicer(object):
   |                       ^^^^^^
41 |     """The greeting service definition.
42 |     """
   |
help: Remove `object` inheritance

UP004 [*] Class `Greeter` inherits from `object`
   --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:99:15
    |
 98 |  # This class is part of an EXPERIMENTAL API.
 99 | class Greeter(object):
    |               ^^^^^^
100 |     """The greeting service definition.
101 |     """
    |
help: Remove `object` inheritance

E501 Line too long (106 > 100)
   --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:148:101
    |
146 |             timeout=None,
147 |             metadata=None):
148 |         return grpc.experimental.stream_unary(request_iterator, target, '/helloworld.Greeter/RecordRoute',
    |                                                                                                     ^^^^^^
149 |             helloworld__pb2.Point.SerializeToString,
150 |             helloworld__pb2.RouteSummary.FromString,
    |

E501 Line too long (105 > 100)
   --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:165:101
    |
163 |             timeout=None,
164 |             metadata=None):
165 |         return grpc.experimental.stream_stream(request_iterator, target, '/helloworld.Greeter/RouteChat',
    |                                                                                                     ^^^^^
166 |             helloworld__pb2.RouteNote.SerializeToString,
167 |             helloworld__pb2.RouteNote.FromString,
    |

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:1:1
  |
1 | / import time
2 | | from flask import Flask
3 | | from flask import request
4 | | import json
5 | | import sys
6 | | import traceback
7 | | import logging
  | |______________^
8 |
9 |   log = logging.getLogger('werkzeug')
  |
help: Organize imports

F401 [*] `time` imported but unused
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:1:8
  |
1 | import time
  |        ^^^^
2 | from flask import Flask
3 | from flask import request
  |
help: Remove unused import: `time`

UP004 [*] Class `CustomProxyFix` inherits from `object`
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:67:22
   |
67 | class CustomProxyFix(object):
   |                      ^^^^^^
68 |     def __init__(self, app):
69 |         self.app = app
   |
help: Remove `object` inheritance

UP030 Use implicit references for positional format fields
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:77:20
   |
75 |         serviceName = environ.get('HTTP_X_FC_SERVICE_NAME', '')
76 |         functionName = environ.get('HTTP_X_FC_FUNCTION_NAME', '')
77 |         if host == "{0}.{1}.fc.aliyuncs.com".format(uid, region) or \
   |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
78 |                 "localhost" in host or \
79 |                 "127.0.0.1" in host:
   |
help: Remove explicit positional indices

UP032 [*] Use f-string instead of `format` call
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:77:20
   |
75 |         serviceName = environ.get('HTTP_X_FC_SERVICE_NAME', '')
76 |         functionName = environ.get('HTTP_X_FC_FUNCTION_NAME', '')
77 |         if host == "{0}.{1}.fc.aliyuncs.com".format(uid, region) or \
   |                    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
78 |                 "localhost" in host or \
79 |                 "127.0.0.1" in host:
   |
help: Convert to f-string

UP030 Use implicit references for positional format fields
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:80:38
   |
78 |                   "localhost" in host or \
79 |                   "127.0.0.1" in host:
80 |               environ['SCRIPT_NAME'] = "/2016-08-15/proxy/{0}/{1}".format(
   |  ______________________________________^
81 | |                 serviceName, functionName)
   | |__________________________________________^
82 |               environ['PATH_INFO'] = environ['PATH_INFO'].replace(
83 |                   environ['SCRIPT_NAME'], "")
   |
help: Remove explicit positional indices

UP032 [*] Use f-string instead of `format` call
  --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:80:38
   |
78 |                   "localhost" in host or \
79 |                   "127.0.0.1" in host:
80 |               environ['SCRIPT_NAME'] = "/2016-08-15/proxy/{0}/{1}".format(
   |  ______________________________________^
81 | |                 serviceName, functionName)
   | |__________________________________________^
82 |               environ['PATH_INFO'] = environ['PATH_INFO'].replace(
83 |                   environ['SCRIPT_NAME'], "")
   |
help: Convert to f-string

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/custom-function/python37/fc-custom-python37-websocket/src/code/server.py:1:1
  |
1 | / import asyncio
2 | | import websockets
  | |_________________^
3 |
4 |   async def echo(websocket, path):
  |
help: Organize imports

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/event-function/fc-event-python2.7/src/code/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 | import logging
  |
help: Remove unnecessary coding comment

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/event-function/fc-event-python3/src/code/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 | import logging
  |
help: Remove unnecessary coding comment

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 |
3 | import logging
  |
help: Remove unnecessary coding comment

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:3:1
  |
1 | # -*- coding: utf-8 -*-
2 |
3 | import logging
  | ^^^^^^^^^^^^^^
4 | HELLO_WORLD = b'Hello world!\n'
  |
help: Organize imports

F401 [*] `logging` imported but unused
 --> docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:3:8
  |
1 | # -*- coding: utf-8 -*-
2 |
3 | import logging
  |        ^^^^^^^
4 | HELLO_WORLD = b'Hello world!\n'
  |
help: Remove unused import: `logging`

F841 Local variable `context` is assigned to but never used
  --> docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:14:5
   |
13 | def handler(environ, start_response):
14 |     context = environ['fc.context']
   |     ^^^^^^^
15 |     request_uri = environ['fc.request_uri']
16 |     for k, v in environ.items():
   |
help: Remove assignment to unused variable `context`

F841 Local variable `request_uri` is assigned to but never used
  --> docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:15:5
   |
13 | def handler(environ, start_response):
14 |     context = environ['fc.context']
15 |     request_uri = environ['fc.request_uri']
   |     ^^^^^^^^^^^
16 |     for k, v in environ.items():
17 |       if k.startswith('HTTP_'):
   |
help: Remove assignment to unused variable `request_uri`

B007 Loop control variable `v` not used within loop body
  --> docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:16:12
   |
14 |     context = environ['fc.context']
15 |     request_uri = environ['fc.request_uri']
16 |     for k, v in environ.items():
   |            ^
17 |       if k.startswith('HTTP_'):
18 |         # process custom request headers
   |
help: Rename unused `v` to `_v`

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:1:1
  |
1 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
2 |
3 | import logging
  |
help: Remove unnecessary coding comment

I001 [*] Import block is un-sorted or un-formatted
 --> docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:3:1
  |
1 | # -*- coding: utf-8 -*-
2 |
3 | import logging
  | ^^^^^^^^^^^^^^
4 | HELLO_WORLD = b'Hello world!\n'
  |
help: Organize imports

F401 [*] `logging` imported but unused
 --> docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:3:8
  |
1 | # -*- coding: utf-8 -*-
2 |
3 | import logging
  |        ^^^^^^^
4 | HELLO_WORLD = b'Hello world!\n'
  |
help: Remove unused import: `logging`

F841 Local variable `context` is assigned to but never used
  --> docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:14:5
   |
13 | def handler(environ, start_response):
14 |     context = environ['fc.context']
   |     ^^^^^^^
15 |     request_uri = environ['fc.request_uri']
16 |     for k, v in environ.items():
   |
help: Remove assignment to unused variable `context`

F841 Local variable `request_uri` is assigned to but never used
  --> docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:15:5
   |
13 | def handler(environ, start_response):
14 |     context = environ['fc.context']
15 |     request_uri = environ['fc.request_uri']
   |     ^^^^^^^^^^^
16 |     for k, v in environ.items():
17 |       if k.startswith('HTTP_'):
   |
help: Remove assignment to unused variable `request_uri`

B007 Loop control variable `v` not used within loop body
  --> docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:16:12
   |
14 |     context = environ['fc.context']
15 |     request_uri = environ['fc.request_uri']
16 |     for k, v in environ.items():
   |            ^
17 |       if k.startswith('HTTP_'):
18 |         # process custom request headers
   |
help: Rename unused `v` to `_v`

UP031 Use format specifiers instead of percent format
  --> docs/example/start-fc-main/publish.py:12:19
   |
10 |         print("----------------------: ", eve_app)
11 |         publish_script = 'https://serverless-registry.oss-cn-hangzhou.aliyuncs.com/publish-file/python3/hub-publish.py'
12 |         command = 'cd %s && wget %s && python hub-publish.py' % (eve_app, publish_script)
   |                   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
13 |         child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, )
14 |         stdout, stderr = child.communicate()
   |
help: Replace with format specifiers

E501 Line too long (103 > 100)
  --> docs/example/start-fc-main/publish.py:13:101
   |
11 |         publish_script = 'https://serverless-registry.oss-cn-hangzhou.aliyuncs.com/publish-file/python3/hub-publish.py'
12 |         command = 'cd %s && wget %s && python hub-publish.py' % (eve_app, publish_script)
13 |         child = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, )
   |                                                                                                     ^^^
14 |         stdout, stderr = child.communicate()
15 |         if child.returncode == 0:
   |

I001 [*] Import block is un-sorted or un-formatted
  --> scripts/ralph/dashboard.py:7:1
   |
 5 |   """
 6 |
 7 | / import json
 8 | | import threading
 9 | | import webbrowser
10 | | import time
11 | | from http.server import BaseHTTPRequestHandler, HTTPServer
12 | | from pathlib import Path
   | |________________________^
13 |
14 |   SCRIPT_DIR = Path(__file__).parent.resolve()
   |
help: Organize imports

I001 [*] Import block is un-sorted or un-formatted
  --> scripts/ralph/ralph.py:6:1
   |
 4 |   """
 5 |
 6 | / import json
 7 | | import sys
 8 | | import subprocess
 9 | | import time
10 | | from pathlib import Path
11 | |
12 | | import dashboard
   | |________________^
13 |
14 |   # 配置
   |
help: Organize imports

F541 [*] f-string without any placeholders
   --> scripts/ralph/ralph.py:210:19
    |
208 |         except KeyboardInterrupt:
209 |             elapsed = time.time() - total_start_time
210 |             print(f"\n\n⚠️  用户中断")
    |                   ^^^^^^^^^^^^^^^^^^
211 |             print(f"⏱️  总运行时间: {format_duration(elapsed)}")
212 |             sys.exit(130)
    |
help: Remove extraneous `f` prefix

UP009 [*] UTF-8 encoding declaration is unnecessary
 --> scripts/test_asr.py:2:1
  |
1 | #!/usr/bin/env python3
2 | # -*- coding: utf-8 -*-
  | ^^^^^^^^^^^^^^^^^^^^^^^
3 | """SoniScope · US-001 E-6 云端语音识别可用性自检脚本.
  |
help: Remove unnecessary coding comment

E501 Line too long (102 > 100)
  --> scripts/test_asr.py:38:101
   |
36 |     # 指定自己的文件 / region / 开启返回词信息
37 |     python test/test_asr.py \\
38 |         --file-link 'https://soniscope-audio.oss-cn-beijing.aliyuncs.com/sample/sample-20s.wav?...' \\
   |                                                                                                     ^^
39 |         --region cn-beijing \\
40 |         --enable-words
   |

B904 Within an `except` clause, raise exceptions with `raise ... from err` or `raise ... from None` to distinguish them from errors in exception handling
   --> scripts/test_asr.py:166:9
    |
164 |             file=sys.stderr,
165 |         )
166 |         raise SystemExit(2)
    |         ^^^^^^^^^^^^^^^^^^^
167 |     return AcsClient(ak_id, ak_secret, region)
    |

E501 Line too long (106 > 100)
   --> scripts/test_asr.py:197:74
    |
195 |         raw = client.do_action_with_exception(request)
196 |     except Exception as exc:  # noqa: BLE001 - POP SDK 抛通用异常
197 |         print(f"✗ 提交任务请求失败（鉴权 / 网络 / 参数错误，立即失败不重试）：\n  {exc}", file=sys.stderr)
    |                                                                                                     ^^^^^^
198 |         raise SystemExit(3) from exc
    |

E501 Line too long (102 > 100)
   --> scripts/test_asr.py:275:84
    |
274 |     if status != STATUS_SUCCESS:
275 |         print("\n✗ 识别未成功。请对照 api-reference-2 §服务状态码 排查 StatusCode。", file=sys.stderr)
    |                                                                                                     ^^
276 |         return "fail"
    |

E501 Line too long (103 > 100)
   --> scripts/test_asr.py:283:79
    |
281 |     print("\n--- 逐句结果（含时间戳，单位 ms）---")
282 |     if not sentences:
283 |         print("  （无句子，可能是纯静音或无有效语音，见状态码 21050003 / ASR_RESPONSE_HAVE_NO_WORDS）")
    |                                                                                                      ^^
284 |     for idx, s in enumerate(sentences, 1):
285 |         print(
    |

Found 89 errors.
[*] 43 fixable with the `--fix` option (19 hidden fixes can be enabled with the `--unsafe-fixes` option).
```

## 门禁 3:miniprogram_lint(仓内自定义门禁,Makefile:168 实体命令直调)

```bash
uv run python -m soniscope_worker lint-miniprogram   # 直调,不经 make;实跑加 --frozen 防 lock 更新
```

**结果:exit=0,通过**(输出中的仓库绝对路径前缀已改写为相对):

```
== 小程序静态检查：apps/miniprogram ==
✅ miniprogram lint passed
```

## 直调后零 diff 快查(Pitfall 6)

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——PASS,三条门禁直调时段内工作树 == 基线
```

## 三态销号表(03-02 填)

核实方法:每条命中经 `git show 5927f36:<path>` 提取命中行及上下文人工判断(D-07 三态);排除目录命中的判定依据为 CHARTER 扫描排除清单的路径归属(人工核对路径前缀)。门禁 3(miniprogram_lint)exit=0 零命中——门禁通过,无命中需销号。行 11-29 为 vendored 目录分文件聚合行(同一文件内命中合并一行,规则@行号逐条列明,条数注于命中列)。

| # | 命中(path:line @ 5927f36) | 规则/模式 | 销号 | 理由/去向 |
|---|---------------------------|-----------|------|-----------|
| 1 | apps/fc/shared/app.py:14 | mypy import-not-found | 确认 | `from handler import handler` 系部署态导入(handler.py 仅在部署 zip 内与 app.py 同目录),仓内直调 mypy 必 exit=1——strict 门禁在仓内结构性不可绿,门禁实态与 Makefile typecheck 目标口径属真实工具链可疑点 → 深挖线索(03-06 Makefile/门禁普审;交叉 03-04 HYP-12 审 app.py 本体) |
| 2 | scripts/test_asr.py:2 | UP009 | 确认 | 门禁规则集(E,F,I,UP,B)内真实违例;scripts/ 未纳入门禁保护面的实证 → 深挖线索(03-06 scripts 普审,HYP-25) |
| 3 | scripts/test_asr.py:38 | E501 | 确认 | 同上,门禁规则集内真实违例(docstring 示例行 102 字符)→ 深挖线索(03-06 scripts 普审,HYP-25) |
| 4 | scripts/test_asr.py:166 | B904 | 确认 | except 内 raise 未带 `from`,违反仓库既定异常链约定(CLAUDE.md "Chain exceptions")且属门禁 B 规则集 → 深挖线索(03-06 scripts 普审,HYP-25) |
| 5 | scripts/test_asr.py:197 | E501 | 确认 | 同 #3,门禁规则集内真实违例 → 深挖线索(03-06 scripts 普审,HYP-25) |
| 6 | scripts/test_asr.py:275 | E501 | 确认 | 同 #3 → 深挖线索(03-06 scripts 普审,HYP-25) |
| 7 | scripts/test_asr.py:283 | E501 | 确认 | 同 #3 → 深挖线索(03-06 scripts 普审,HYP-25) |
| 8 | scripts/ralph/dashboard.py:7 | I001 | 误报 | CHARTER 排除清单 #2(scripts/ralph/ 为 agent 元工具,非部署/验证工具链审计对象);存在级问题已按 D-09 口径另行承接 |
| 9 | scripts/ralph/ralph.py:6 | I001 | 误报 | 同 #8,排除清单 #2 |
| 10 | scripts/ralph/ralph.py:210 | F541 | 误报 | 同 #8,排除清单 #2 |
| 11 | docs/example/start-fc-main/async-task/python3/src/code/async-task/index.py:1,2,15(3 条) | UP009@1 / I001@2 / UP032@15 | 误报 | CHARTER 排除清单 #1(vendored 外部仓库非项目代码);vendored 膨胀之存在级问题按 D-09 承接,不逐条立案(以下 vendored 行同此理由) |
| 12 | docs/example/start-fc-main/async-task/python3/src/code/dest-fail/index.py:1,13(2 条) | UP009@1 / UP032@13 | 误报 | 同 #11,排除清单 #1 |
| 13 | docs/example/start-fc-main/async-task/python3/src/code/dest-succ/index.py:1,13(2 条) | UP009@1 / UP032@13 | 误报 | 同 #11 |
| 14 | docs/example/start-fc-main/custom-container-function/fc-custom-container-event-python3.9/src/code/app.py:1,56(2 条) | I001@1 / E501@56 | 误报 | 同 #11 |
| 15 | docs/example/start-fc-main/custom-container-function/fc-custom-container-no-web-server-event-fibonacci/app.py:1,1,2(3 条) | I001@1 / F401@1 / F401@2 | 误报 | 同 #11 |
| 16 | docs/example/start-fc-main/custom-container-function/fc-custom-container-websocket-python3.9/src/code/app.py:1(1 条) | I001@1 | 误报 | 同 #11 |
| 17 | docs/example/start-fc-main/custom-function/f#/fc-custom-fsharp-http/src/init_helper.py:8(1 条) | UP015@8 | 误报 | 同 #11 |
| 18 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-event/src/code/server.py:1,1,2(3 条) | I001@1 / F401@1 / F401@2 | 误报 | 同 #11 |
| 19 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_client.py:3,3,40,46,55,56,57,58,70,77(10 条) | UP010@3 / I001@3 / UP031@40,46,55,56,57,58,70,77 | 误报 | 同 #11 |
| 20 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/greeter_server.py:1,48(2 条) | I001@1 / UP031@48 | 误报 | 同 #11 |
| 21 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2.py:1,5,16,20,23,24-39(21 条) | UP009@1 / I001@5 / E501@16,23 / E712@20 / F821@24-39(×16) | 误报 | 同 #11(protoc 生成代码,文件头自注 DO NOT EDIT) |
| 22 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-grpc/src/code/helloworld_pb2_grpc.py:3,8,40,99,148,165(6 条) | I001@3 / UP004@8,40,99 / E501@148,165 | 误报 | 同 #11(gRPC 生成代码) |
| 23 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-http/src/code/server.py:1,1,67,77,77,80,80(7 条) | I001@1 / F401@1 / UP004@67 / UP030@77,80 / UP032@77,80 | 误报 | 同 #11 |
| 24 | docs/example/start-fc-main/custom-function/python37/fc-custom-python37-websocket/src/code/server.py:1(1 条) | I001@1 | 误报 | 同 #11 |
| 25 | docs/example/start-fc-main/event-function/fc-event-python2.7/src/code/index.py:1(1 条) | UP009@1 | 误报 | 同 #11 |
| 26 | docs/example/start-fc-main/event-function/fc-event-python3/src/code/index.py:1(1 条) | UP009@1 | 误报 | 同 #11 |
| 27 | docs/example/start-fc-main/http-function/fc-http-python2.7/src/code/index.py:1,3,3,14,15,16(6 条) | UP009@1 / I001@3 / F401@3 / F841@14,15 / B007@16 | 误报 | 同 #11 |
| 28 | docs/example/start-fc-main/http-function/fc-http-python3/src/code/index.py:1,3,3,14,15,16(6 条) | UP009@1 / I001@3 / F401@3 / F841@14,15 / B007@16 | 误报 | 同 #11 |
| 29 | docs/example/start-fc-main/publish.py:12,13(2 条) | UP031@12 / E501@13 | 误报 | 同 #11 |

**聚合行条数复算:** 行 11-29 覆盖 vendored 命中 3+2+2+2+3+1+1+3+10+2+21+6+7+1+1+1+6+6+2 = 80 条;行 8-10 覆盖 scripts/ralph 3 条;行 2-7 覆盖 test_asr.py 6 条;行 1 为 mypy 唯一命中。

**对账等式:** 确认 7 + 误报 83 + 移交 0 = 命中总数 90(mypy 1 + ruff 89 + miniprogram_lint 0)✓

**移交说明:** 本档无移交项。

## 阶段收尾零 diff 验证记录(03-01 Task 3 收尾,CHARTER D-03)

```bash
git diff --stat 5927f36 -- apps/ scripts/ docs/
# 实际输出:(空)——apps/、scripts/、docs/ 相对基线零改动(全部仪器运行完毕后复验)
```
