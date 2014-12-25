# -*- coding: utf-8 -*-
import copy

import pytest

from sefaria.model import *
from sefaria.model.text import SchemaNode, SchemaContentNode, SchemaStructureNode, JaggedArrayNode, JaggedArrayCommentatorNode, StringNode
from sefaria.system.exceptions import IndexSchemaError


class Test_Validate(object):
    def test_jaggedarray_fields(self):

        j = JaggedArrayNode()
        j.add_title(u"title1", "en", primary=True)\
         .add_title(u"ייי", "he", primary=True)\
         .add_title(u"title2", "en")\
         .add_title(u"ייכי", "he")
        j.depth = 1
        j.sectionNames = ["Foo"]
        j.addressTypes = ["Integer"]
        j.key = "bob"

        j.validate()

        for f in ["depth", "sectionNames", "addressTypes", "key"]:
            t = copy.deepcopy(j)
            delattr(t, f)

            with pytest.raises(IndexSchemaError):
                t.validate()

        t = copy.deepcopy(j)
        t.sectionNames += ["foob"]
        with pytest.raises(IndexSchemaError):
            t.validate()

        t = copy.deepcopy(j)
        t.addressTypes += ["Integer"]
        with pytest.raises(IndexSchemaError):
            t.validate()


    def test_validate_children(self):
        """
        Does validate fall through to children?
        """
        s = SchemaStructureNode()
        s.key = "root"
        s.add_title("root", "en", primary=True)
        j = JaggedArrayNode()
        j.add_title("child", "en", primary=True)
        j.key = "child"
        j.depth = 1
        j.sectionNames = ["Foo"]
        j.append_to(s)

        with pytest.raises(IndexSchemaError):
            s.validate()


class Test_Titles(object):

    def test_add(self):
        j = JaggedArrayNode()
        j.add_title(u"title1", "en", primary=True)
        j.add_title(u"ייי", "he", primary=True)
        j.add_title(u"title2", "en")
        j.add_title(u"ייכי", "he")
        assert len(j.all_node_titles("he")) == 2
        assert len(j.all_node_titles("en")) == 2

        assert j.primary_title("en") == u"title1"
        j.add_title(u"title3", "en", primary=True, replace_primary=True)
        assert len(j.all_node_titles("en")) == 3
        assert len(j.all_node_titles("he")) == 2
        assert j.primary_title("en") == u"title3"

    def test_remove(self):
        j = JaggedArrayNode()
        j.add_title(u"title1", "en", primary=True)\
         .add_title(u"ייי", "he", primary=True)\
         .add_title(u"title2", "en")\
         .add_title(u"ייכי", "he")
        j.remove_title(u"title1", "en")
        j.depth = 1
        j.sectionNames = ["Foo"]
        j.addressTypes = ["Integer"]
        j.key = "bob"

        with pytest.raises(IndexSchemaError):
            j.validate()

    def test_presentation(self):
        s = SchemaStructureNode()
        s.key = "root"
        s.add_title("root", "en", primary=True)

        j = JaggedArrayNode()
        j.key = "child1"
        j.depth = 1
        j.sectionNames = ["Foo"]
        j.addressTypes = ["Integer"]
        j.add_title("Child 1", "en", primary=True)
        j.add_title("Sweet Child", "en", presentation="alone")
        j.add_title("Sweet Child of Mine", "en", presentation="both")
        s.append(j)

        td = s.title_dict()
        assert len(td) == 5

        target = {
            'root': s,
            'root, Child 1': j,
            'root, Sweet Child of Mine': j,
            'Sweet Child of Mine': j,
            'Sweet Child': j,
        }

        assert td == target

    def test_grandchild_presentation(self):
        s = SchemaStructureNode()
        s.key = "root"
        s.add_title("root", "en", primary=True)
        s.add_title("alt root", "en")

        s2 = SchemaStructureNode()
        s2.key = "l2"
        s2.add_title("Level 2", "en", primary=True)
        s2.add_title("Level 2 Alone", "en", presentation="alone")
        s2.add_title("Level 2 Both", "en", presentation="both")
        s2.append_to(s)

        j = JaggedArrayNode()
        j.key = "child1"
        j.depth = 1
        j.sectionNames = ["Foo"]
        j.addressTypes = ["Integer"]
        j.add_title("Level 3a", "en", primary=True)
        j.add_title("Level 3a alone", "en", presentation="alone")
        j.add_title("Level 3a both", "en", presentation="both")
        j.append_to(s2)

        j2 = JaggedArrayNode()
        j2.key = "child2"
        j2.depth = 1
        j2.sectionNames = ["Foo"]
        j2.addressTypes = ["Integer"]
        j2.add_title("Level 3b", "en", primary=True)
        j2.add_title("Level 3b alone", "en", presentation="alone")
        j2.add_title("Level 3b both", "en", presentation="both")
        j2.append_to(s2)

        td = s.title_dict()
        assert len(td) == 36

        target = {
            "root": s,
            "alt root": s,
            "Level 2 Alone": s2,
            "Level 3b alone": j2,
            "Level 3a alone": j,
            "Level 2 Both": s2,
            "Level 3a both": j,
            "Level 3b both": j2,

            "root, Level 2 Both": s2,
            "root, Level 2": s2,
            "alt root, Level 2 Both": s2,
            "alt root, Level 2": s2,

            "root, Level 2 Both, Level 3a": j,
            "root, Level 2, Level 3a": j,
            "alt root, Level 2 Both, Level 3a": j,
            "alt root, Level 2, Level 3a": j,
            "Level 2 Alone, Level 3a": j,
            "Level 2 Both, Level 3a": j,

            "root, Level 2 Both, Level 3a both": j,
            "root, Level 2, Level 3a both": j,
            "alt root, Level 2 Both, Level 3a both": j,
            "alt root, Level 2, Level 3a both": j,
            "Level 2 Alone, Level 3a both": j,
            "Level 2 Both, Level 3a both": j,

            "root, Level 2 Both, Level 3b": j2,
            "root, Level 2, Level 3b": j2,
            "alt root, Level 2 Both, Level 3b": j2,
            "alt root, Level 2, Level 3b": j2,
            "Level 2 Alone, Level 3b": j2,
            "Level 2 Both, Level 3b": j2,

            "root, Level 2 Both, Level 3b both": j2,
            "root, Level 2, Level 3b both": j2,
            "alt root, Level 2 Both, Level 3b both": j2,
            "alt root, Level 2, Level 3b both": j2,
            "Level 2 Alone, Level 3b both": j2,
            "Level 2 Both, Level 3b both": j2,
        }

        assert td == target





    def test_duplicate_primary(self):
        with pytest.raises(IndexSchemaError):
            j = JaggedArrayNode()
            j.add_title(u"title1", "en", primary=True)
            j.add_title(u"title2", "en", primary=True)

        with pytest.raises(IndexSchemaError):
            j = JaggedArrayNode()
            j.add_title(u"ייי", "he", primary=True)
            j.add_title(u"ייעי", "he", primary=True)