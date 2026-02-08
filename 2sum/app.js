// LeetCode 2 Sum problem. Some liberties were taken. this program doesnt take a preset array. It will ask you to enter numbers into an array and then ask for the number you are looking for
//it will also alert the user if the searched number is not a possible sum in the array.

const submit_Button = document.getElementById("submit");
const user_Input = document.getElementById("input");
const submit_Button1 = document.getElementById("submit1");
const user_Input1 = document.getElementById("input1");
let user_Array = [];
let searched_Num = 0;
let solution = [];

function submit_Click() {
    let value = parseInt(user_Input.value, 10); 
    let value1 = parseInt(user_Input1.value,10);
    if (!isNaN(value)) {                       
        user_Array.push(value);
    } 
    if (!isNaN(value1)){
        if (searched_Num === 0) {
            searched_Num = value1;
        }
    }
    user_Input.value = ""; 
    user_Input1.value = "";
};

function calculate() {
    console.log(user_Array);
    console.log(searched_Num);

    for (let i = 0; i < user_Array.length; i++) {
        if (solution.length != 0) {
            break;
        }
        for (let o = i + 1; o < user_Array.length; o++) {
            let sum = user_Array[i] + user_Array[o]; 
            if (sum === searched_Num) {
                solution.push(i, o);
                console.log("The solution is:\n");
                console.log(solution);
                break;
            }
        }
    }
}

submit_Button.addEventListener("click",submit_Click);
submit_Button1.addEventListener("click",calculate);