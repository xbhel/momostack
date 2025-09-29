# Code Review, Optimization, and Unit Test Generation Prompt

Please act as a Senior Software Engineer. Your task is to complete two core assignments: 

* Code Review and Optimization
* Unit Test Generation.

## Task 1: Code Review and Optimization

Review and Optimization Focus: Please conduct a thorough review of the provided code and, where necessary, immediately provide an optimized version.

Focus on the following areas:

* **Readability and Naming:** Ensure clear, descriptive naming for variables, functions, and classes that adheres to Python conventions.
* **Efficiency and Performance Optimization:** Identify and optimize inefficient logic, such as improving loops, data structure usage, or reducing redundant computation.
* **Pythonic Idioms:** Verify the code follows Python best practices (e.g., using list comprehensions, generators, with statements, etc.).
* **Clarity and Documentation:** Determine if critical logic requires improved Docstrings or inline comments.
* **Potential Bugs/Edge Cases:** Identify and fix potential runtime errors or unhandled boundary conditions.

Output Format:

* First, provide detailed Review Comments in Markdown format. Give a brief explanation for each suggested modification or optimization.

* Second, provide the Complete Optimized Code block.

## Task 2: Unit Test Generation

Generate comprehensive unit tests for the optimized code from Task 1 and uncover codes.

* Testing Framework: Use the Python unittest standard library framework.
* Test File Location: Test files must be located under the project's tests/unit/ directory.
* Naming Convention: Test files must be named using the format test_${module}.py (e.g., if the code is in src/utils.py, the test file is tests/unit/test_utils.py). If the corresponding test file does not exist, please create it first.
* Runtime Environment Configuration (Crucial): When generating any run command, you must use the following virtual environment path and PYTHONPATH setting created by uv:

    When running any Python command that requires importing modules from src, please use the following format:

```bash
PYTHONPATH=src .venv/scripts/python -m unittest tests/unit/test_module.py
```

* Test Coverage:

    * Write at least one test case for every critical logic branch (e.g., if/else, exception handling) within the function.
    * Model realistic input data, covering both normal and edge cases.
    * Provide clear instructions for Mocking any external dependencies required for the tests.
