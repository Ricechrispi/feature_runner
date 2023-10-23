import argparse
import os
import logging
import json

logger = logging.getLogger("instance_checker")
logger.setLevel("DEBUG")
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
# create formatter
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
# add formatter to ch
ch.setFormatter(formatter)
# add ch to logger
logger.addHandler(ch)


def make_report(reports, output_file_prefix):

    output_file_name = "_".join([output_file_prefix, "report.txt"])
    with open(output_file_name, "w") as output_file:

        def log_and_write(s):
            logger.info(s)
            output_file.write(f"{s}\n")

        num_files_errors = 0
        num_files_warnings = 0
        unique_errors = {}
        unique_warnings = {}
        # The amount of chars that are significant for a message to be considered unique
        # If you decrease it, you will have more report summary output. (and vice versa)
        significant_chars = 30
        for report in reports:
            if len(report["error_lines"]) > 0:
                num_files_errors += 1
            if len(report["warn_lines"]) > 0:
                num_files_warnings += 1

            for err_line in report["error_lines"]:
                if err_line[:significant_chars] not in unique_errors.keys():
                    unique_errors[err_line[:significant_chars]] = 1
                else:
                    unique_errors[err_line[:significant_chars]] += 1

            for warn_line in report["warn_lines"]:
                if warn_line[:significant_chars] not in unique_warnings.keys():
                    unique_warnings[warn_line[:significant_chars]] = 1
                else:
                    unique_warnings[warn_line[:significant_chars]] += 1

        log_and_write(f"Processed {len(reports)} files.")
        log_and_write(f"There are {num_files_errors} files with errors.")
        log_and_write(f"There are {num_files_warnings} files with warnings.")
        log_and_write(20 * "-")

        log_and_write("Summary of the errors:")
        log_and_write(20 * "-")
        for key, value in unique_errors.items():
            log_and_write(f"Error type: '{key}...' Times found: {value}")
        log_and_write(20 * "-")

        log_and_write("Summary of the warnings:")
        log_and_write(20 * "-")
        for key, value in unique_warnings.items():
            log_and_write(f"Warning type: '{key}...' Times found: {value}")
        log_and_write(20 * "-")

    dump_file_name = "_".join([output_file_prefix, "dump.json"])
    with open(dump_file_name, "w") as dump_file:
        for report in reports:
            report["max_found_dvars"] = max(report["found_dvars"])
            del report["found_dvars"]
            dump_file.write(str(json.dumps(report, indent=2)))
            dump_file.write("\n\n")


def check_file(instance):

    report = {"instance_name": instance,
              "num_vars": 0,
              "num_clauses": 0,
              "p_line": False,
              "found_clauses": 0,
              "found_dvars": set(),
              "projection": None,
              "file_name": None,
              "file_type": None,
              "ft": "mc",
              "weights": None,
              "dupweight": False, # Note: checking for duplicate weights is currently not supported
              "info_lines": [],
              "warn_lines": [],
              "error_lines": [],
              }

    # simple wrappers to both log results and to return them later
    def log_err(s):
        logger.error(s)
        report["error_lines"].append(s)

    def log_warn(s):
        logger.warning(s)
        report["warn_lines"].append(s)

    def log_info(s):
        logger.info(s)
        report["info_lines"].append(s)

    log_info(f"Checking file: {instance}")

    with open(instance, "r") as instance_file:
        lines = instance_file.readlines()
        for i, line in enumerate(lines):
            line = line.strip()
            if len(line) == 0: # skip empty lines
                continue

            elif line.startswith("c t "):
                parts = line.split()
                if len(parts) >= 3:
                    report["file_type"] = parts[2] # the thing after t
                else:
                    log_err(f"File type in header has unexpected format. Line: '{line}'")
                    break

            elif line.startswith("p"):
                parts = line.split()
                if len(parts) >= 4:
                    report["num_vars"], report["num_clauses"] = int(parts[2]), int(parts[3])
                    report["p_line"] = True
                else:
                    log_err(f"P line has unexpected format. Line: '{line}'")
                    break

            elif line.startswith("c file "):
                parts = line.split()
                if len(parts) >= 3:
                    report["file_name"] = line.split()[2]
                    if report["file_name"] != os.path.basename(instance):
                        log_err(f"Filename in header was {report['file_name']}, expected: {os.path.basename(instance)}")
                else:
                    log_err(f"File name line has unexpected format. Line: '{line}'")
                    break

            elif line.startswith("c p weight "):
                log_info("INSTANCE is a weighted model counting instance")
                if report["ft"] == 'pmc':
                    report["ft"] = 'pwmc'
                else:
                    report["ft"] = 'wmc'

                if not line.endswith(' 0'):
                    log_err(f"WEIGHT LINE {i}: not terminated by 0. WAS '{line}'")
                    break

            elif line.startswith("c p show "):
                log_info("INSTANCE is a projected model counting instance")
                if report["ft"] == 'wmc': #always mc for now
                    report["ft"] = 'pwmc'
                else:
                    report["ft"] = 'pmc'

                if not line.endswith(' 0'):
                    log_err(f"PROJ LINE {i}: not terminated by 0. Line: '{line}'")
                    break

                try:
                    # this splits the line into each component, and then tries to makes ints from them
                    line = map(int, line.split()[3:-1])
                    report["projection"] = set(line)
                except ValueError as e:
                    log_err(f"LINE {i}: has an unknown format. Line: '{line}'")
                    break

            elif line.startswith('c'): # skip normal comment lines
                continue

            else: # normal case

                try:
                    int_parts = map(int, line.split()[:-1])
                    for var in int_parts:
                        report["found_dvars"].add(abs(var))
                except ValueError as e:
                    log_err(f"LINE {i}: has an unknown format. Line: '{line}'")
                    break

                if not line.endswith(' 0'):
                    log_err(f"LINE {i}: not terminated by 0. Line: '{line}'")
                    break
                report["found_clauses"] += 1

    if len(report["error_lines"]) > 0:
        log_info("Error lines are present. Aborting further analysis.")
        return report

    if not report["p_line"]:
        log_err("Header is missing.")

    if report["found_clauses"] != report["num_clauses"]:
        log_err(f"Number of clauses does not match with the header. "
                f"Found clauses {report['found_clauses']}. Header announced {report['num_clauses']}.")
        if report["found_clauses"] > report["num_clauses"]:
            log_err(f"More clauses than announced.")

    if report["file_type"] is None:
        log_warn("File type is missing")

    elif report["file_type"] != report["ft"]:
        log_err(f"Wrong filetype. Expected {report['ft']}. Announced was {report['file_type']}")

    max_found_nvars = max(report["found_dvars"])
    if max_found_nvars != report["num_vars"]:
        log_warn(f"Num of vars doesn't match with header. Found variables {max_found_nvars}. Header announced {report['num_vars']}.")

        if max_found_nvars > report["num_vars"]:
            log_err(f"More variables than announced.")

        elif max_found_nvars < report["num_vars"]:
            unused = []
            for x in set(range(1, report["num_vars"])) - report["found_dvars"]:
                unused.append(x)
            log_warn(f"Found some unused variables. Variables: {unused}")

    consecutive = True
    missing_ids = []
    for i in range(1, max_found_nvars + 1):
        if not i in report["found_dvars"]:
            missing_ids.append(i)
            consecutive = False
    if not consecutive:
        log_warn(f"Variables are not consecutive. The missing ids:  {missing_ids}")

    if report["projection"] is not None:
        if max(report["projection"]) > max_found_nvars:
            log_err(f"Some projected variables are unknown.")

    if report["dupweight"]:
        log_err("Instance contains duplicate weight entries for the same literal.")

    if report["weights"] is not None:
        for key, value in report["weights"].items():
            if abs(key) > max_found_nvars:
                log_err(f"Weights: Variable {abs(key)} does not exist.")
            if value <= 0 or value > 1:
                log_warn(f"Weight for variable:{key} is {value} ~(0<=value<=1)")
            try:
                w = report["weights"][-key]
                if value + w > 1 and not (report["weights"][key] == report["weights"][-key] == 1):
                    log_warn(f"Weights of literals {key}/{-key} do not add to 1 ({value + w}={value}+{w})")
            except KeyError as e:
                log_err(f"Weight for literal: {-key} missing while there is one {key}.")

        occurrences = {}
        # Check for duplicate weights
        for key, value in sorted(report["weights"].items(), key=lambda l: abs(l[0])):
            if key in occurrences:
                occurrences[key] += 1
            else:
                occurrences[key] = 1

        for key, value in filter(lambda k: k[1] > 1, occurrences.items()):
            log_err(f"Duplicate weight for {key}. Occured {value} times.")

    if report["file_name"] is None:
        log_warn("Filename in header was missing.")

    return report


def check_folder(folder):
    reports = []
    instances = [os.path.abspath(os.path.join(folder, f)) for f in os.listdir(folder) if f.endswith(".cnf")]
    for instance in  instances:
        reports.append(check_file(instance))
    return reports


def parse_args():
    parser = argparse.ArgumentParser()
    exclusive_args = parser.add_mutually_exclusive_group()
    exclusive_args.add_argument("--instance_folder", dest="instance_folder", type=str)
    exclusive_args.add_argument("--instance", dest="instance", type=str)
    parser.add_argument("--output_file_prefix", type=str, default="instance_checker")
    args = parser.parse_args()
    return args


def main():
    args = parse_args()
    if args.instance_folder is not None:
        reports = check_folder(args.instance_folder)
    elif args.instance is not None:
        reports = [check_file(args.instance)]
    else:
        raise ValueError("Neither instance nor folder was supplied.")

    make_report(reports, args.output_file_prefix)


if __name__ == "__main__":
    main()