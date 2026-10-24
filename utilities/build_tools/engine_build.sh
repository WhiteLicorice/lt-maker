# Build Script for lt_engine
# Run from the repository root: ./utilities/build_tools/engine_build.sh <project>
# source ./venv/Scripts/activate
if [ "$#" -ne 1 ];
then
    echo 'Error: expected one argument (name of the project)'
    exit 2
fi
name=$1

# Same icon the editor's Build Project uses
icon="favicon.ico"
if [ -f "$name.ltproj/resources/system/favicon.ico" ];
then
    icon="$name.ltproj/resources/system/favicon.ico"
fi

python -m app.engine.codegen.source_generator
python -m PyInstaller -y ./utilities/build_tools/engine.spec -- "$name" "$icon" || exit 1

rm -rf "../$name"
mkdir "../$name"
# mkdir "../$name/$name"
mv "dist/$name" "../$name/$name"
# cp utilities/audio_dlls/* "../$name/$name"
# cp -r favicon.ico "../$name/$name"
cp utilities/install/double_click_to_play.bat "../$name"

version=$(python -m app.constants)
echo "$version" > "../$name/$name/metadata.txt"

# Now zip up directory
# rm -f "../$name.zip"
# backup="../$name_v${version}.zip"
# rm -f "$backup"
# 7z a "../$name.zip" "../$name"
# cp "../$name.zip" "$backup"

echo Done
