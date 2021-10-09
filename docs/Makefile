# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line, and also
# from the environment for the first two.
SPHINXOPTS    ?=
SPHINXBUILD   ?= sphinx-build
SOURCEDIR     = .
BUILDDIR      = man

ifeq ($(shell which $(SPHINXBUILD) >/dev/null 2>&1; echo $$?), 1)
$(error The '$(SPHINXBUILD)' command was not found.)
endif

.PHONY: man Makefile clean

man:
	$(SPHINXBUILD) -b man $(SOURCEDIR) $(BUILDDIR)/

clean:
	rm -rf $(BUILDDIR)/*
