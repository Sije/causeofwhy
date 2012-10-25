# Copyright (C) 2012 Brian Wesley Baugh
"""Provides document analysis and answer extraction functions and classes."""
import indexer


class AnswerEngine(object):
    """Provides the methods to turn a query into a list of answers.

    Attributes:
        query: The direct query string from the user.
        ir_query: The regularize string sent to the IR index.
        num_pages: The number of pages returned by the IR search.
        pages: Ranked list of Page objects returned by the IR search.
            The number of pages is usually less than num_pages unless
            during the call to __init__() the value for num_top is
            greater than or equal to num_pages.
        answers: List of Answer objects generated by the class.
    """

    def __init__(self, index, query, start=0, num_top=10):
        """Inits AnswerEngine by querying the IR module to get Page objects.

        Args:
            index: An indexer.Index object, which represent the IR system.
            query: The direct query string from the user.
            start: The number of pages to offset from the beginning of the
                page list returned by the index.
            num_top: The number of pages (from the top of the ranked list
                of pages (sorted by similarity) returned by the index) to
                extract answers from.
                Combined withe the start-argument, this allows for paging
                through the results by only looking at a certain number of
                pages at a time.
        """
        self.query = query
        self.answers = None
        # Candidate Document Selection
        self.ir_query = indexer.regularize(indexer.tokenizer.tokenize(self
                                                                      .query))
        page_sim = index.ranked(self.ir_query)
        self.num_pages = len(page_sim)
        # Reduce number of pages we need to get from disk
        page_sim = page_sim[start:num_top]
        page_ids, similarity = zip(*page_sim)
        # Retrieve the Page objects from the list of Page.IDs
        self.pages = index.get_page(page_ids)
        # Tell each page the value of its similarity score
        for page, sim in zip(self.pages, similarity):
            page.cosine_sim = sim

    def _analyze_pages(self):
        """Performs candidate document analysis and information extraction."""
        for page in self.pages:
            page.preprocess()
            page.tokenize_sentences()

    def _extract_answers(self):
        """Extract answers from the pages using all the tagged information.

        This method should be run only after _analyze_pages().
        """
        answers = []
        for page in self.pages:
            page_windows = []
            for sentence in page.sentences:
                if len(page_windows) == 3:
                    break
                if any(term in indexer.regularize(sentence) for term in
                       self.ir_query):
                    page_windows.append(Answer(page, ' '.join(sentence)))
            answers.extend(page_windows)
        self.answers = answers

    def get_answers(self):
        """Performs answer extraction after processing the Page documents.

        This method is a convenience method to call the appropriate
        candidate document analysis and other information extraction
        methods in the appropriate order.

        Returns:
            A list of Answer objects representing the answers extracted
            from the internal list of (relevant) Pages. This list is also
            available by accessing the answers attribute of the instance.
        """
        self._analyze_pages()
        self._extract_answers()
        return self.answers


class Answer:
    """Represents a single answer."""

    def __init__(self, page, text):
        """Initializes the Answer object with the Page and answer text."""
        self.page = page
        self.text = text


def get_answers(ans_eng):
    """Calls the get_answers() method of the provided AnswerEngine object.

    This is a convenience method for the multiprocessing module, as that
    module is unable to pickle bound methods (methods belonging to class
    instance). Instead, this function can be used by providing the
    AnswerEngine as an argument.

    Args:
        ans_eng: The AnswerEngine object to call get_answers() on.

    Returns:
        The list of Answer objects provided by the AnswerEngine.
    """
    return ans_eng.get_answers()