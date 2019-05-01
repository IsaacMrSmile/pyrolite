import io
import os
import numpy as np
import pandas as pd
from pathlib import Path
from ..pd import to_frame, to_ser, to_numeric
from ...geochem.ind import __common_elements__, __common_oxides__
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def to_meltsfile(
    ser, linesep=os.linesep, writetraces=True, modes=[], exclude=[], **kwargs
):
    """
    Converts a series to a MELTSfile text representation. It requires 'title'
    and 'initial composition' lines, major elements to be represented as oxides
    in Wt% and trace elements in µg/g.

    Parameters
    ----------
    ser : :class:`pandas.Series`
        Series to convert to a melts file.
    linesep : :class:`str`
        Line separation character.
    writetraces : :class:`bool`
        Whether to include traces in the output file.
    modes : :class:`list`
        List of modes to use (e.g. 'isobaric', 'fractionate solids').
    exclude : :class:`list`
        List of chemical components to exclude from the meltsfile.

    Returns
    -------
    :class:`str`
        String representation of the meltsfile, which can be immediately written to a
        file object.

    Todo
    -----
        * Parameter validation.
    """
    lines = []
    ser = to_ser(ser)
    assert ("Title" in ser.index) or ("title" in ser.index)
    if "Title" in ser.index:
        lines.append("Title: {}".format(ser.Title))
    else:
        lines.append("Title: {}".format(ser.title))
    majors = [i for i in ser.index if i in __common_oxides__ and not i in exclude]
    for k, v in zip(majors, ser.loc[majors].values):
        if not pd.isnull(v):  # no NaN data in MELTS files
            lines.append("Initial Composition: {} {}".format(k, v))

    if writetraces:
        traces = [i for i in ser.index if i in __common_elements__ and not i in exclude]
        for k, v in zip(traces, ser.loc[traces].values):
            if not pd.isnull(v):  # no NaN data in MELTS files
                lines.append("Initial Trace: {} {}".format(k, v))

    for param in ["Temperature", "Pressure"]:
        for subparam in ["Initial", "Final", "Increment"]:
            k = " ".join([subparam, param])
            if k in ser.index:
                v = ser[k]
                if not pd.isnull(v):  # no NaN data in MELTS files
                    lines.append("{}: {}".format(k, v))

    for k in ["dp/dt", "log fo2 path", "log fo2 delta"]:
        par = [
            par for ix, par in enumerate(ser.index.tolist()) if par.lower() == k.lower()
        ]
        if par:
            par = par[0]
            v = ser[par]
            if not pd.isnull(v):  # no NaN data in MELTS files
                lines.append("{}: {}".format(k, v))

    for m in modes:
        lines.append("Mode: {}".format(m))

    # valid_modes = ["Fractionate Solids", "Fractionate"]
    return linesep.join(lines)


def to_meltsfiles(df, linesep=os.linesep, **kwargs):
    """
    Creates a number of melts files from a dataframe.

    Parameters
    -----------
    df : :class:`pandas.DataFrame`
        Dataframe from which to take the rows and create melts files.
    linesep : :class:`str`
        Line separation character.

    Returns
    -------
    :class:`list`
        List of strings which can be written to file objects.
    """

    # Type checking such that series will be passed directly to MELTSfiles
    if isinstance(df, pd.DataFrame):
        return [
            to_meltsfile(df.iloc[ix, :], linesep=os.linesep, **kwargs)
            for ix in range(df.index.size)
        ]
    elif isinstance(df, pd.Series):
        return [to_meltsfile(df, linesep=os.linesep, **kwargs)]


def from_meltsfile(filename):
    """
    Read from a meltsfile into a :class:`pandas.DataFrame`.

    Parameters
    -----------
    filename : :class:`str` | :class:`pathlib.Path` | :class:`io.BytesIO`
        Filename, filepath or bytes object to read from.

    Returns
    --------
    :class:`pandas.DataFrame`
        Dataframe containing meltsfile parameters.
    """
    if isinstance(filename, io.BytesIO):
        file = filename.getvalue().decode()
    elif isinstance(filename, io.StringIO):
        file = filename.getvalue()
    else:
        try:  # filepath
            with open(filename) as fh:
                file = filename.read()
        except FileNotFoundError:  # string specification of meltsfile
            file = filename

    lines = [line.split(": ") for line in file.splitlines() if line.strip()]
    fmtlines = []
    for ix, args in enumerate(lines):
        if args[0].strip().lower() in ["initial composition", "initial trace"]:
            fmtlines.append(args[1].strip().split())
        else:
            fmtlines.append([i.strip() for i in args])
    df = to_numeric(
        pd.DataFrame.from_records(fmtlines).set_index(0, drop=True)[1], errors="ignore"
    )
    return df
