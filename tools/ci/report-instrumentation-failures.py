#!/usr/bin/env python3
import glob
import xml.etree.ElementTree as xml
for path in glob.glob('app/build/outputs/androidTest-results/connected/debug/**/TEST-*.xml', recursive=True):
    for case in xml.parse(path).iter('testcase'):
        failure = case.find('failure')
        if failure is None:
            failure = case.find('error')
        if failure is None:
            continue
        name = f"{case.get('classname')}.{case.get('name')}"
        message = (failure.get('message') or failure.text or 'no failure message').replace('\r', ' ').replace('\n', ' ')
        print(f"::error title=Instrumentation failure: {name}::{message[:1000]}")
