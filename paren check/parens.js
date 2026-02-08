//push() → adds to the end (top of stack)

//pop() → removes from the end (top of stack)

//peek → you can see the top with stack[stack.length - 1]


let test_String = "{[()]}()[{}](({}))";
let stack = [];

function solution() {
    let mapping = {
        ')': '(',
        ']': '[',
        '}': '{'
    };

    for (let char of test_String) {
        if (char === '(' || char === '[' || char === '{') {
            // opening bracket =push to stack
            stack.push(char);
        } else if (char === ')' || char === ']' || char === '}') {
            // closing bracket =check top of stack
            if (stack.length === 0 || stack[stack.length - 1] !== mapping[char]) {
                console.log("String is NOT valid");
                return;
            }
            stack.pop(); // match found → pop it
        }
    }

    if (stack.length === 0) {
        console.log("String is valid");
    } else {
        console.log("String is NOT valid");
    }
}

solution();
