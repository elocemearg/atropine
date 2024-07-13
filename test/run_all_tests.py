#!/usr/bin/python3

import sys
import os
import subprocess
import time

def main():
    test_timeout_sec = 600

    # Find which directory this file is in
    full_exe_path = os.path.abspath(__file__)
    full_exe_path = os.path.realpath(full_exe_path)
    test_dir = os.path.dirname(full_exe_path)
    atropine_root_dir = os.path.dirname(test_dir)

    # If there is no "logs" directory, create it
    logs_dir = os.path.join(test_dir, "logs")
    if not os.path.exists(logs_dir):
        os.mkdir(logs_dir)

    # Open tests.txt
    test_names = []
    with open(os.path.join(test_dir, "tests.txt")) as tests:
        for line in tests:
            test_names.append(line.strip())

    tests_run = 0
    tests_failed = 0
    total_start_time = time.time()
    for test_name in test_names:
        test_py_path = os.path.join(test_dir, test_name)

        command = [ sys.executable, test_py_path ]
        test_stdout_name = os.path.join(logs_dir, test_name + ".stdout")
        test_stderr_name = os.path.join(logs_dir, test_name + ".stderr")

        with open(test_stdout_name, "w") as test_stdout, open(test_stderr_name, "w") as test_stderr:
            sys.stderr.write("%3d/%d %-40s " % (tests_run + 1, len(test_names), test_name))
            start_time = time.time()
            p = subprocess.run(command, stdout=test_stdout, stderr=test_stderr, cwd=atropine_root_dir, timeout=test_timeout_sec)
            tests_run += 1
            end_time = time.time()
            elapsed_time = end_time - start_time
            if p.returncode == 0:
                print("passed  %6.2fs" % (elapsed_time), file=sys.stderr)
            else:
                tests_failed += 1
                print("FAILED  %6.2fs" % (elapsed_time), file=sys.stderr)
                print("Log files for %s:" % (test_name), file=sys.stderr)
                print("\t" + test_stdout_name, file=sys.stderr)
                print("\t" + test_stderr_name, file=sys.stderr)

    total_end_time = time.time()
    total_elapsed_time = total_end_time - total_start_time

    print("", file=sys.stderr)
    print("Total time: %7.2fs." % (total_elapsed_time))
    if tests_failed == 0:
        print("All %d tests passed." % (tests_run))
        retcode = 0
    else:
        print("%d tests passed, %d tests failed." % (tests_run - tests_failed, tests_failed))
        retcode = 1

    sys.exit(retcode)

if __name__ == "__main__":
    main()
