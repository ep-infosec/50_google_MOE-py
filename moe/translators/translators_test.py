#!/usr/bin/env python
#
# Copyright 2011 Google Inc. All Rights Reserved.

"""Tests for moe.translators."""

__author__ = 'dbentley@google.com (Daniel Bentley)'

from google.apputils import basetest

from moe import base
from moe import codebase_utils
from moe import moe_app
import test_util
from moe.translators import translators


def setUp():
  moe_app.InitForTest()


class TranslatorsTest(basetest.TestCase):

  def testRunsScrubber(self):
    t = translators.ScrubberInvokingTranslator(
        'public', 'internal',
        {'rearranging_config': {
            'mappings': [
                {'input_prefix': 'src',
                 'output_prefix': 'internal_src_dir'
                }
                ]
            }
        })
    input_dir = test_util.TestResourceFilename(
        'translators/simple/input/')
    input_codebase = codebase_utils.Codebase(path=input_dir)
    try:
      generated_codebase = t.Translate(input_codebase)
    except NotImplementedError:
      # For now, public MOE can't build the scrubber, so this won't work.
      # Patches appreciated!
      return
    difference = base.AreCodebasesDifferent(
        generated_codebase,
        codebase_utils.Codebase(test_util.TestResourceFilename(
            'translators/simple/expected/')))
    self.assertFalse(difference)

  def testIdentityRemembersAdditionalFilesRe(self):
    t = translators.IdentityTranslator('public', 'internal')
    input_dir = test_util.TestResourceFilename(
        'translators/additional_files/input/')
    input_codebase = codebase_utils.Codebase(
        path=input_dir,
        additional_files_re='bar')
    generated_codebase = t.Translate(input_codebase)

    equivalent_codebase = codebase_utils.Codebase(
        path=test_util.TestResourceFilename(
            'translators/without_additional_file/'))
    without_additional_files_re = codebase_utils.Codebase(
        path=input_dir)

    self.assertFalse(base.AreCodebasesDifferent(
        input_codebase, generated_codebase))

    self.assertFalse(base.AreCodebasesDifferent(
        generated_codebase, equivalent_codebase))

    self.assert_(base.AreCodebasesDifferent(
        without_additional_files_re, equivalent_codebase))

  def testTranslateToProjectSpace(self):
    class MockTranslator(object):
      def FromProjectSpace(self):
        return 'foo'

      def ToProjectSpace(self):
        return 'bar'

      def Translate(self, unused_codebase):
        path = test_util.TestResourceFilename('codebases/modified_python/')
        return codebase_utils.Codebase(path, project_space='bar')

    foo_creator = test_util.StaticCodebaseCreator(
        {'1001': 'simple_python'}, project_space='foo')
    created_codebase = foo_creator.Create('1001')
    translated_codebase = translators.TranslateToProjectSpace(
        created_codebase, 'foo', [MockTranslator()])
    self.assertEqual('foo', created_codebase.ProjectSpace())
    self.assertEqual('foo', translated_codebase.ProjectSpace())
    self.assertEqual(created_codebase, translated_codebase)

    translated_codebase = translators.TranslateToProjectSpace(
        created_codebase, 'bar', [MockTranslator()])
    self.assertEqual('bar', translated_codebase.ProjectSpace())

    self.assertRaises(
        base.Error,
        translators.TranslateToProjectSpace,
        created_codebase, 'baz', [MockTranslator()])


if __name__ == '__main__':
  basetest.main()
