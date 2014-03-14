import csv
import tempfile
import splunk.Intersplunk
import os
import subprocess
import traceback
import sys
from splunk.clilib import cli_common as cli
import base64

try:
    (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
    if isgetinfo:
        splunk.Intersplunk.outputInfo(
            streaming=False,  # because it only runs on a search head
            generating=False,
            retevs=False,
            reqsop=False,
            preop=None,
            timeorder=True,
            clear_req_fields=False,
            req_fields=None
        )

    keywords, kvs = splunk.Intersplunk.getKeywordsAndOptions()
    #splunk.Intersplunk.parseError(",".join(keywords))

    if len(sys.argv) < 2:
        splunk.Intersplunk.parseError("Missing actual R script parameter")
    r_snippet = sys.argv[1]

    #read configuration file
    cli.cacheConfFile('r')
    r_config = cli.confSettings['r']

    #check if the R library presence
    r_path_config = r_config['paths']
    r_path = r_path_config.get('r')
    if not os.path.exists(r_path):
        splunk.Intersplunk.outputResults(
            splunk.Intersplunk.generateErrorResults('Cannot find R executable at path \'%s\'' % r_path))
        exit(0)

    #make sure that custom script files exists
    r_temp_dir = os.path.join(tempfile.gettempdir(), 'r')
    if not os.path.exists(r_temp_dir):
        os.makedirs(r_temp_dir)
    script_stanza_prefix = 'script://'
    for stanza_name in r_config:
        if stanza_name.startswith(script_stanza_prefix):
            script_stanza = r_config[stanza_name]
            script_content = base64.decodestring(script_stanza['content'])
            script_filename = stanza_name[len(script_stanza_prefix):]+'.r'
            script_full_path = os.path.join(r_temp_dir, script_filename)
            with open(script_full_path, 'wb') as f:
                f.write(script_content)

    #read all the input data
    input_data = splunk.Intersplunk.readResults()

    #collect field names
    fieldnames = set()
    for result in input_data:
        for key in list(result.keys()):
            if not key in fieldnames:
                fieldnames.add(key)
    fieldnames = list(fieldnames)
    if len(fieldnames) == 0:
        fieldnames = None

    input_csv_filename = None
    output_csv_filename = None
    script_filename = None
    r_output_filename = None
    try:
        #create CSV input file
        if fieldnames:
            with tempfile.NamedTemporaryFile(delete=False) as f:
                input_csv_filename = f.name
                writer = csv.DictWriter(f, fieldnames=list(fieldnames))
                writer.writeheader()
                writer.writerows(input_data)
        #create CSV output file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            output_csv_filename = f.name
        #create script file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            script_filename = f.name
            if input_csv_filename:
                f.write('input <- read.csv("' + input_csv_filename.replace('\\', '\\\\') + '")\n')
            f.write(r_snippet + '\n')
            f.write('write.csv(output, file = "' + output_csv_filename.replace('\\', '\\\\') + '")\n')
        #create r output file
        with tempfile.NamedTemporaryFile(delete=False) as f:
            r_output_filename = f.name

        #with open(input_csv_filename, "r") as f:
        #    splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(f.read()))
        #    exit(0)

        command = "\"" + r_path + "\" --vanilla" + " < \"" + script_filename + "\" > \"" + r_output_filename + "\""
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            cwd=r_temp_dir
        )
        output, error = process.communicate()
        if error is not None and len(error) > 0:
            splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(error))
            exit(0)
        if output is not None and len(output) > 0:
            splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(output))
            exit(0)

        #with open(output_csv_filename, "r") as f:
        #    splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(f.read()))
        #    exit(0)

        #read csv output
        output = []
        with open(output_csv_filename, "r") as f:
            reader = csv.reader(f)
            rows = [row for row in reader]
            if len(rows) == 0:
                splunk.Intersplunk.outputResults([])
                exit(0)
            header_row = rows[0]
            for row in rows[1:]:
                event = {}
                for i, cell in enumerate(row):
                    event[header_row[i]] = cell
                output.append(event)

        splunk.Intersplunk.outputResults(output)

    #delete temp files
    finally:
        if input_csv_filename:
            os.remove(input_csv_filename)
        if output_csv_filename:
            os.remove(output_csv_filename)
        if script_filename:
            os.remove(script_filename)
        if r_output_filename:
            os.remove(r_output_filename)

except Exception as e:
    splunk.Intersplunk.outputResults(splunk.Intersplunk.generateErrorResults(str(e) + ": " + traceback.format_exc()))
