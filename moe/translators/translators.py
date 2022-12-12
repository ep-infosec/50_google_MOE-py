#!/usr/bin/env python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Tools to translate codebases in one project space into another.

A central concept of MOE is the Project Space. One project leads different lives
in different repositories. (E.g., it needs a Makefile in the public project,
and a different type of build file internally.) Translators let us take a
codebase in the internal project space and generate a codebase in the public
project space.

"""

__author__ = 'dbentley@google.com (Daniel Bentley)'


import os
import tempfile

import json as simplejson

from google.apputils import resources

from moe import base
from moe import codebase_utils
from moe import moe_app


class Translator(object):
  """Interface for Translators."""

  def FromProjectSpace(self):
    """Name of the project space this translates from."""
    raise NotImplementedError

  def ToProjectSpace(self):
    """Name of the project space this translates to."""
    raise NotImplementedError

  def Translate(self, codebase):
    """Generate the translation of 'codebase'.

    Args:
      codebase: codebase_utils.Codebase, the codebase to translate

    Returns:
      codebase_utils.Codebase, the translated Codebase

    Raises:
      base.Error if there was a problem translating
    """
    raise NotImplementedError


class ScrubberInvokingTranslator(Translator):
  """A translator that invokes the MOE scrubber to translate."""

  def __init__(self, from_project_space, to_project_space, scrubber_config):
    Translator.__init__(self)
    self._from_project_space = from_project_space
    self._to_project_space = to_project_space

    # NB(dbentley): it's important that this scrubber config have the same
    # ignore_files_re as the codebase that is to be translated's
    # additional_files_re, but because of encapsulation it's hard to check
    # that.
    self._scrubber_config = scrubber_config

  def FromProjectSpace(self):
    return self._from_project_space

  def ToProjectSpace(self):
    return self._to_project_space

  def Translate(self, codebase):
    # TODO(dbentley): locate the scrubber
    raise NotImplementedError

    task = moe_app.RUN.ui.BeginImmediateTask(
        'translate',
        'Translating from %s project space to %s (using scrubber at %s)' %
        (self._from_project_space, self._to_project_space, scrubber_path))

    with task:
      if codebase.ProjectSpace() != self._from_project_space:
        raise base.Error(
            ('Attempting to translate Codebase %s from project space %s to %s, '
             'but it is in project space %s') %
            (codebase, self._from_project_space, self._to_project_space,
             codebase.ProjectSpace()))

      (output_tar_fd, output_tar_filename) = tempfile.mkstemp(
          dir=moe_app.RUN.temp_dir,
          prefix='translated_codebase_',
          suffix='.tar')
      os.close(output_tar_fd) # We use the name only, to pass to a subprocess.
      # TODO(dbentley): should this be a CodebaseCreationError?
      base.RunCmd(scrubber_path,
                  ['--output_tar', output_tar_filename,
                   '--config_data', simplejson.dumps(self._scrubber_config),
                   codebase.ExpandedPath()])

      return codebase_utils.Codebase(output_tar_filename,
                                     project_space=self._to_project_space)


class IdentityTranslator(Translator):
  """A translator that translates by doing nothing."""

  def __init__(self, from_project_space, to_project_space):
    Translator.__init__(self)
    self._from_project_space = from_project_space
    self._to_project_space = to_project_space

  def FromProjectSpace(self):
    return self._from_project_space

  def ToProjectSpace(self):
    return self._to_project_space

  def Translate(self, codebase):
    task = moe_app.RUN.ui.BeginImmediateTask(
        'translate',
        'Translating from %s project space to %s (using identity translation)' %
        (self._from_project_space, self._to_project_space))

    with task:
      if codebase.ProjectSpace() != self._from_project_space:
        raise base.Error(
            ('Attempting to translate Codebase %s from project space %s to %s, '
             'but it is in project space %s') %
            (codebase, self._from_project_space, self._to_project_space,
             codebase.ProjectSpace()))

      return codebase_utils.Codebase(
          codebase.ExpandedPath(),
          additional_files_re=codebase.AdditionalFilesRe(),
          project_space=self._to_project_space)


def TranslateToProjectSpace(codebase, to_project_space, translators):
  """Translate codebase into to_project_space using translators.

  Args:
    codebase: codebase_utils.Codebase
    to_project_space: str
    translators: seq of Translator
  """
  original_project_space = codebase.ProjectSpace()
  if original_project_space == to_project_space:
    return codebase
  for t in translators:
    if (t.FromProjectSpace() == original_project_space and
        t.ToProjectSpace() == to_project_space):
      return t.Translate(codebase)
  else:
    # TODO(dbentley): should this be a CodebaseCreationError?
    raise base.Error('Could find no translator from %s to %s' %
                     (repr(original_project_space), repr(to_project_space)))
