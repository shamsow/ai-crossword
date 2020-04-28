import sys

from crossword import *
from collections import deque
from itertools import combinations

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        # dict with variables as keys and a list of invalid words as values
        rm = {}
        for var, options in self.domains.items():
            rm[var] = []
            # note all words that are not the required length
            for option in options:
                if len(option) != var.length:
                    rm[var] += [option]
        # remove words that are not the correct length
        for var in rm:
            inc = set(rm[var])
            self.domains[var] = self.domains[var] - inc


    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        revision = False
        overlaps = self.crossword.overlaps

        if overlaps[(x, y)] is not None:
            # get the index for each each word that must match
            x_index, y_index = overlaps[(x, y)]
            # set of all words in domain of x that are invalid for the words in y
            invalid = set()
            for x_word in self.domains[x]:
                check = []
                for y_word in self.domains[y]:
                    if x_word[x_index] != y_word[y_index]:
                        check.append(True)
                    else:
                        check.append(False)
                # if the word is not compatible with any words in y, it is invalid
                if all(check):
                    invalid.add(x_word)
                    revision = True
            # remove invalid values
            self.domains[x] = self.domains[x] - invalid
        return revision

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        # add all overlapping variables to queue
        if arcs is None:
            queue = list(combinations(self.crossword.variables, 2))
            queue = deque([(i, j) for i, j in queue if self.crossword.overlaps[(i, j)] is not None])
        else:
            queue = deque(arcs)
        # loop until all arcs in queue have been considered
        while queue:
            # enforce arc consistency one by one
            X,Y = queue[0]
            queue.popleft()
            if self.revise(X, Y):
                # if domain of X is empty, there is no solution
                if len(self.domains[X]) == 0:
                    return False
            # add new arcs to queue because the previous revision changed the consistency
            for neighbor in self.crossword.neighbors(X):
                if neighbor == Y:
                    continue
                queue.append((neighbor, X))
        return True


    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        # if the number of variables in assignment matches the number of all variables, assignment is complete
        if len(assignment) == len(self.crossword.variables):
            return True
        return False


    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        # check if any word has been assigned twice
        words = [i for i in assignment.values()]
        for word in words:
            if words.count(word) > 1:
                return False
        # check if overlaps are correct
        variables = [i for i in assignment]
        for var in variables:
            neigbors = [i for i in self.crossword.neighbors(var) if i in variables]
            for neighbor in neigbors:
                var_index, neighbor_index = self.crossword.overlaps[(var, neighbor)]
                if assignment[var][var_index] != assignment[neighbor][neighbor_index]:
                    return False
        return True


    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        order = {}
        # find the number of values ruled out in neighbors domain for each word in the domain of var
        neighbors = self.crossword.neighbors(var)
        for word in self.domains[var]:
            count = 0
            for neighbor in neighbors:
                # ignore neighbors that have already been assigned a word
                if neighbor not in assignment and word in self.domains[neighbor]:
                    count += 1
            order[word] = count
        # return the word that rules out the least number of words in the domain of neighboring variables
        return sorted(order, key=lambda x: order[x])

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        # get list of unassigned variables
        variables = [i for i in self.domains if i not in assignment]
        # dict of heuristics for each variable
        h = {}
        for var in variables:
            domain = len(self.domains[var])
            degree = len(self.crossword.neighbors(var))
            h[var] = (domain, degree)
        # sort the variables according to the minimum remaining values in domain
        remaining = sorted(h, key=lambda x: h[x][0])
        # check for a tie between top two variables
        if len(remaining) > 1 and h[remaining[0]][0] == h[remaining[1]][0]:
            # if there is a tie return the var with the highest degree
            lowest = {remaining[0]: h[remaining[0]], remaining[1]: h[remaining[1]]}
            return sorted(lowest, key=lambda x: lowest[x][1])[-1]
        # return variable with smallest remaining values in domain
        return remaining[0]

    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        # if assignment is completer return result
        if self.assignment_complete(assignment):
            print(assignment)
            return assignment

        # Try a new variable
        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            new_assignment = assignment.copy()
            new_assignment[var] = value
            if self.consistent(new_assignment):
                result = self.backtrack(new_assignment)
                if result is not None:
                    return result
        return None


def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python3 generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
