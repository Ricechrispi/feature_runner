import subprocess
import argparse
import csv
import os
import logging
from concurrent.futures import ThreadPoolExecutor


logger = logging.getLogger(__name__)
logger.setLevel("DEBUG")
# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)


# Returns a certain amount instances found in a folder as a list of strings.
# If amount is -1, all instances are returned
def get_instances(instance_folder, amount=-1):
    instances = []
    iteration = 0
    for file in os.listdir(instance_folder):
        filename = os.fsdecode(file)
        if filename.endswith(".cnf"):
            iteration += 1
            if amount != -1 and iteration > amount:
                break
            instances.append(os.path.join(instance_folder, filename))
    return instances


def instance_features(instance):
    cmd = ["bin/satzilla/features"]
    # -lp and -ls do not work
    arguments = ["-base", "-unit", "-sp", "-dia", "-cl", "-lobjois", instance]
    cmd.extend(arguments)

    process = subprocess.run(cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True)

    stderr_lines = [line.strip() for line in process.stderr.split("\n")]
    stdout_lines = [line.strip() for line in process.stdout.split("\n")]

    logger.debug("---------------STDERR--------------")
    for line in stderr_lines:
        if len(line) > 0:
            logger.debug(line)
    logger.debug("---------------STDOUT--------------")
    for line in stdout_lines:
        if len(line) > 0:
            logger.debug(line)

    feature_names = None
    feature_values = None
    if len(stdout_lines) >= 4:
        feature_names = stdout_lines[-3].split(",") #TODO more robust, i.e. parse from end until found, if len > 0 and no err
    if len(stdout_lines) >= 3:
        feature_values = stdout_lines[-2].split(",")

    return feature_names, feature_values


def create_feature_row(instance):
    header = ["instance_name"]
    values = [os.path.basename(instance)]

    # calculate the features
    feature_names, feature_values = instance_features(instance)
    if feature_names is None or feature_values is None:
        # Something went wrong, return the instance name for debugging
        logger.info(f"Could not calculate features for instance: {instance}")
        return [instance], None

    # extend with the rest of the features
    header.extend(feature_names)
    values.extend(feature_values)
    return header, values


def combine_feature_files(combined_file, feature_list, header):
    if feature_list is None or len(feature_list) == 0 \
            or header is None or len(header) == 0 or header[0] is None:
        logger.error(f"There is nothing to save, all instance calculations failed.")
        return

    with open(combined_file, "w") as c_file:
        csv_writer = csv.writer(c_file, delimiter=",")
        lines = [header]
        lines.extend(feature_list)
        logger.debug(f"lines for combined file: {lines}")
        csv_writer.writerows(lines)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--instance", dest="instance", type=str)
    parser.add_argument("--instance_folder", dest="instance_folder", type=str)
    parser.add_argument("--combined_file", dest="combined_file", type=str, default="features.csv")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if (args.instance is None and args.instance_folder is None) or \
            (args.instance is not None and args.instance_folder is not None):
        raise ValueError("Please provide either an instance or a folder")

    if args.instance is not None:
        instances = [args.instance]
    else:
        instances = get_instances(instance_folder=args.instance_folder)

    with ThreadPoolExecutor(max_workers=6) as executor:
        result = executor.map(create_feature_row, instances)
        executor.shutdown(wait=True)

    feature_list = []
    common_header = None
    for header, values in result:
        if values is None:
            logger.error(f"Error while calculating features of instance {header[0]}. Skipping.")
            continue
        feature_list.append(values)
        if common_header is None:
            common_header = header
        else:
            assert common_header == header

    combine_feature_files(combined_file=args.combined_file,
                          feature_list=feature_list, header=common_header)


if __name__ == "__main__":
    main()
