#!/bin/bash

# Generate Linux and Windows standalone-build scripts in the buildscripts dir.

HTTP_SERVICE_HANDLER_MODULE_IMPORTS=""
DYNAMIC_PAGE_MODULE_IMPORTS=""
GENERATOR_MODULE_IMPORTS=""

for f in py/servicehandlers/*.py; do
    b=$(basename "$f" | sed 's/\.py//')
    HTTP_SERVICE_HANDLER_MODULE_IMPORTS="$HTTP_SERVICE_HANDLER_MODULE_IMPORTS --hidden-import $b"
done

for f in py/dynamicpages/*.py; do
    b=$(basename "$f" | sed 's/\.py//')
    DYNAMIC_PAGE_MODULE_IMPORTS="$DYNAMIC_PAGE_MODULE_IMPORTS --hidden-import $b"
done

for f in generators/*.py; do
    b=$(basename "$f" | sed 's/\.py//')
    GENERATOR_MODULE_IMPORTS="$GENERATOR_MODULE_IMPORTS --hidden-import $b"
done

# Build the script for building a Linux standalone executable
cat >buildscripts/build_linux_standalone.sh <<EOF
#!/bin/bash

pyinstaller --onefile --distpath ./out/dist --workpath ./out/build -p py/ -p py/servicehandlers/ -p py/dynamicpages/ -p generators/ $HTTP_SERVICE_HANDLER_MODULE_IMPORTS $DYNAMIC_PAGE_MODULE_IMPORTS $GENERATOR_MODULE_IMPORTS --add-data ./webroot:webroot ./atropine.py

exit $?
EOF
chmod u+x buildscripts/build_linux_standalone.sh

# Generate file_version_info.txt
ATROPINE_VERSION=$(python3 -c "import sys; sys.path.append('py'); from countdowntourney import SW_VERSION_SPLIT; print(' '.join([ str(x) for x in SW_VERSION_SPLIT ]));")
ATROPINE_VERSION_ARRAY=( $ATROPINE_VERSION )
ATROPINE_MAJOR=${ATROPINE_VERSION_ARRAY[0]}
ATROPINE_MEDIUM=${ATROPINE_VERSION_ARRAY[1]}
ATROPINE_MINOR=${ATROPINE_VERSION_ARRAY[2]}
ATROPINE_TINY=0
CURRENT_YEAR=$(date "+%Y")

cat >buildscripts/windows_file_version_info.txt <<EOF
# Comments and annotations helpfully provided by pyi-grab_version
#
# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    # filevers and prodvers should be always a tuple with four items: (1, 2, 3, 4)
    # Set not needed items to zero 0.
    filevers=($ATROPINE_MAJOR, $ATROPINE_MEDIUM, $ATROPINE_MINOR, $ATROPINE_TINY),
    prodvers=($ATROPINE_MAJOR, $ATROPINE_MEDIUM, $ATROPINE_MINOR, $ATROPINE_TINY),
    # Contains a bitmask that specifies the valid bits 'flags'
    mask=0x3f,
    # Contains a bitmask that specifies the Boolean attributes of the file.
    flags=0x0,
    # The operating system for which this file was designed.
    # 0x4 - NT and there is no need to change it.
    OS=0x4,
    # The general type of file.
    # 0x1 - the file is an application.
    fileType=0x1,
    # The function of the file.
    # 0x0 - the function is not defined for this fileType
    subtype=0x0,
    # Creation date and time stamp.
    date=(0, 0)
    ),
  kids=[
    StringFileInfo(
      [
      StringTable(
        '000004b0',
        [StringStruct('CompanyName', ''),
        StringStruct('FileDescription', 'Atropine'),
        StringStruct('FileVersion', '${ATROPINE_MAJOR}.${ATROPINE_MEDIUM}.${ATROPINE_MINOR}.${ATROPINE_TINY}'),
        StringStruct('InternalName', 'Atropine'),
        StringStruct('LegalCopyright', '2014-${CURRENT_YEAR} Graeme Cole'),
        StringStruct('OriginalFilename', 'atropine.exe'),
        StringStruct('ProductName', 'Atropine'),
        StringStruct('ProductVersion', '${ATROPINE_MAJOR}.${ATROPINE_MEDIUM}.${ATROPINE_MINOR}.${ATROPINE_TINY}')])
      ]), 
    VarFileInfo([VarStruct('Translation', [0, 1200])])
  ]
)
EOF

# Generate build_windows_standalone.bat - must be run on a Windows system from
# the directory above buildscripts.
cat >buildscripts/build_windows_standalone.bat <<EOF
REM    This batch file must be run on a Windows computer, from the directory
REM    above the buildscripts directory. It requires pyinstaller.

pyinstaller --onefile -p py -p py\\servicehandlers -p py\\dynamicpages -p generators $HTTP_SERVICE_HANDLER_MODULE_IMPORTS $DYNAMIC_PAGE_MODULE_IMPORTS $GENERATOR_MODULE_IMPORTS --add-data .\\webroot:webroot .\\atropine.py

pyi-set_version .\\buildscripts\\windows_file_version_info.txt .\\dist\\atropine.exe
EOF
