#!/usr/bin/python3

import os;

def get_fixture_generator_list():
    gendir = os.environ.get("GENERATORPATH", ".");

    file_list = os.listdir(gendir);

    module_list = [];
    for f in file_list:
        if f.endswith(".py") and f.startswith("fixgen_"):
            module_list.append(f[0:-3]);
        module_list = sorted(module_list)
    return module_list;
