#! /usr/bin/env bash --

. ~/.bashrc;

PATH=${PATH};

app=$(basename $0);

# Default values for options
geometry='300x300';

# Usage message
USAGE="
NAME
    $app - create thumbnail images from input png files

SYNOPSIS
    $app [hxv] [-o OUTPUT_PATH] [-g WIDTHxVALUE] png_file(s)

DESCRIPTION

    Create thumbnails with geometry=${geometry} for all input .png files. Thumbnails
    are written to the same directory as the source files.

    -h
        show help message

    -o OUTPUT_PATH
        specify an alternate output path for the thumbnails

    -g WIDTHxHEIGHT
        specify an alternate thumbnail WIDTH and HEIGHT. Both values must be specified 
        and separated by an 'x'

    -v
        verbose output. Print the full path of the thumbnail

    -x
        debug mode. Print paths but do not create the thumbnail images.

";

# Process options
while getopts "hxo:g:v" option
do
    case "$option" in
        "h")
            echo -e "$USAGE";
            exit 0;
            ;;
        "o")
            output_path="$OPTARG";
            ;;
        "g")
            geometry="$OPTARG";
            ;;
        "v")
            verbose=1;
            ;;
        "x")
            debug=1;
            ;;
        "?")
            echo -e "$USAGE" >&2;
            exit 1;
            ;;
    esac
done

# Remove option from $@
shift $((OPTIND-1));

if [ "$#" -eq 0 ]
then
    echo "No image files specified" >&2;
    echo "$USAGE" >&2;
    exit 1;
fi

if [ -n "$output_path" -a ! -d "$output_path" ]
then
    echo "Invalid destination path specified: $output_path" >&2;
    exit 1;
fi

# Validate geometry
width=$(echo $geometry -Fx '{print $1}');
if [ -z "$width" ]
then
    echo "Invalid width (1st value) for geometry: $geometry";
    exit 1;
fi
height=$(echo $geometry -Fx '{print $2}');
if [ -z "$height" ]
then
    echo "Invalid height (2nd value) for geometry: $geometry";
    exit 1;
fi

height=$(echo $geometry -Fx '{print $2}');

for i in "$@"
do

    # original png directory name
    png_path=$(dirname $i);
    # original png file name
    orig_png=$(basename $i); 
    # Make sure the input file ends in .png
    ext=${orig_png:(-4)};
    [ "$ext" != '.png' ] && continue;

    # Create the name of the thumbnail image
    thumb="$(echo $orig_png | awk 'BEGIN{FS=OFS="_"}{NF--; print}')_tn.png";

    # Fully qualified path to the thumbnail
    if [ -n "$output_path" ]
    then
        thumb_dest="${output_path}/${thumb}";
    else
        thumb_dest="${png_path}/${thumb}";
    fi

    # Print the path to the thumbnail but do not create it
    if [ -n "$debug" ]
    then
        echo "Skipping thumbnail conversion (-x): $thumb_dest" >&2;
        continue;
    fi

    # Create the thumbnail
    convert $i \
        -thumbnail \
        $geometry \
        $thumb_dest;

    # continue if failed
    [ "$?" -ne 0 ] && continue;

    # continute if -v not specified
    [ -z "$verbose" ] && continue;

    # print the name of the created thumbnail
    echo "${thumb_dest}";

done

