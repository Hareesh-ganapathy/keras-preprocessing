import importlib
import inspect
import re
from itertools import compress

import pytest

modules = ['keras_preprocessing',
           'keras_preprocessing.image',
           'keras_preprocessing.sequence',
           'keras_preprocessing.text']

# Tokenizer is being refactored PR #106
accepted_name = ['set_keras_submodules', 'get_keras_submodule', 'Tokenizer']
accepted_module = []

# Functions or classes with less than 'MIN_CODE_SIZE' lines can be ignored
MIN_CODE_SIZE = 10


def handle_class_init(name, member):
    init_args = [
        arg for arg in list(inspect.signature(member.__init__).parameters.keys())
        if arg not in ['self', 'args', 'kwargs']
    ]
    assert_args_presence(init_args, member.__doc__, member, name)


def handle_class(name, member):
    if is_accepted(name, member):
        return

    if member.__doc__ is None and not member_too_small(member):
        raise ValueError("{} class doesn't have any documentation".format(name),
                         member.__module__, inspect.getmodule(member).__file__)

    handle_class_init(name, member)

    for n, met in inspect.getmembers(member):
        if inspect.ismethod(met):
            handle_method(n, met)


def handle_function(name, member):
    if is_accepted(name, member) or member_too_small(member):
        # We don't need to check this one.
        return
    doc = member.__doc__
    if doc is None:
        raise ValueError("{} function doesn't have any documentation".format(name),
                         member.__module__, inspect.getmodule(member).__file__)

    args = list(inspect.signature(member).parameters.keys())
    assert_args_presence(args, doc, member, name)
    assert_function_style(name, member, doc, args)
    assert_doc_style(name, member, doc)


def assert_doc_style(name, member, doc):
    lines = doc.split("\n")
    first_line = lines[0]
    if len(first_line.strip()) == 0:
        raise ValueError(
            "{} the documentation should be on the first line.".format(name),
            member.__module__)
    first_blank = [i for i, line in enumerate(lines) if not line.strip()]
    if len(first_blank) > 0:
        if lines[first_blank[0] - 1].strip()[-1] != '.':
            raise ValueError("{} first line should end with a '.'".format(name),
                             member.__module__)


def assert_function_style(name, member, doc, args):
    code = inspect.getsource(member)
    has_return = re.findall(r"\s*return \S+", code, re.MULTILINE)
    if has_return and "# Returns" not in doc:
        innerfunction = [inspect.getsource(x) for x in member.__code__.co_consts if
                         inspect.iscode(x)]
        return_in_sub = [ret for code_inner in innerfunction for ret in
                         re.findall(r"\s*return \S+", code_inner, re.MULTILINE)]
        if len(return_in_sub) < len(has_return):
            raise ValueError("{} needs a '# Returns' section".format(name),
                             member.__module__)

    has_raise = re.findall(r"^\s*raise \S+", code, re.MULTILINE)
    if has_raise and "# Raises" not in doc:
        innerfunction = [inspect.getsource(x) for x in member.__code__.co_consts if
                         inspect.iscode(x)]
        raise_in_sub = [ret for code_inner in innerfunction for ret in
                        re.findall(r"\s*raise \S+", code_inner, re.MULTILINE)]
        if len(raise_in_sub) < len(has_raise):
            raise ValueError("{} needs a '# Raises' section".format(name),
                             member.__module__)

    if len(args) > 0 and "# Arguments" not in doc:
        raise ValueError("{} needs a '# Arguments' section".format(name),
                         member.__module__)

    assert_blank_before(name, member, doc, ['# Arguments', '# Raises', '# Returns'])


def assert_blank_before(name, member, doc, keywords):
    doc_lines = [x.strip() for x in doc.split('\n')]
    for keyword in keywords:
        if keyword in doc_lines:
            index = doc_lines.index(keyword)
            if doc_lines[index - 1] != '':
                raise ValueError(
                    "{} '{}' should have a blank line above.".format(name, keyword),
                    member.__module__)


def is_accepted(name, member):
    if 'keras_preprocessing' not in str(member.__module__):
        return True
    return name in accepted_name or member.__module__ in accepted_module


def member_too_small(member):
    code = inspect.getsource(member).split('\n')
    return len(code) < MIN_CODE_SIZE


def assert_args_presence(args, doc, member, name):
    args_not_in_doc = [arg not in doc for arg in args]
    if any(args_not_in_doc):
        raise ValueError(
            "{} {} arguments are not present in documentation ".format(name, list(
                compress(args, args_not_in_doc))), member.__module__, member)
    words = doc.replace('*', '').split()
    # Check arguments styling
    styles = [arg + ":" not in words for arg in args]
    if any(styles):
        raise ValueError(
            "{} {} are not style properly 'argument': documentation".format(
                name,
                list(compress(args, styles))),
            member.__module__)

    # Check arguments order
    indexes = [words.index(arg + ":") for arg in args]
    if indexes != sorted(indexes):
        raise ValueError(
            "{} arguments order is different from the documentation".format(name),
            member.__module__, indexes)


def handle_method(name, member):
    if name in accepted_name or member.__module__ in accepted_module:
        return
    handle_function(name, member)


def handle_module(mod):
    for name, mem in inspect.getmembers(mod):
        if inspect.isclass(mem):
            handle_class(name, mem)
        elif inspect.isfunction(mem):
            handle_function(name, mem)
        elif 'keras_preprocessing' in name and inspect.ismodule(mem):
            # Only test keras_preprocessing' modules
            handle_module(mem)


def test_doc():
    for module in modules:
        mod = importlib.import_module(module)
        handle_module(mod)


if __name__ == '__main__':
    pytest.main([__file__])
