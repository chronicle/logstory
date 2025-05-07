#!/bin/bash
# Copyright 2025 Google LLC
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

cd cloudfunction-code/entities-function-3day/ && \
touch chronicle-replay-entities-source-3day.zip && \
rm chronicle-replay-entities-source-3day.zip && \
zip -r chronicle-replay-entities-source-3day.zip . && \
cd - && cd cloudfunction-code/entities-function-24h/ && \
touch chronicle-replay-entities-source-24h.zip && \
rm chronicle-replay-entities-source-24h.zip && \
zip -r chronicle-replay-entities-source-24h.zip . && \
cd - && cd cloudfunction-code/events-function-24h/ && \
touch chronicle-replay-events-source-24h.zip && \
rm chronicle-replay-events-source-24h.zip && \
zip -r chronicle-replay-events-source-24h.zip . && \
cd - && \
cd cloudfunction-code/events-function-3day/ && \
touch chronicle-replay-events-source-3day.zip && \
rm chronicle-replay-events-source-3day.zip && \
zip -r chronicle-replay-events-source-3day.zip . && \
cd - && \
cd cloudfunction-code/rule-creator && \
touch chronicle-rule-creator-source.zip && \
rm chronicle-rule-creator-source.zip && \
zip -r chronicle-rule-creator-source.zip . &&
cd -
