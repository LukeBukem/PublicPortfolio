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
    let map = new Map();
    

    for (let i = 0; i < user_Array.length; i++) {
        let need = searched_Num - user_Array[i];
        if (map.has(need)){
            solution.push(map.get(need),i);
            console.log(user_Array[solution[0]],user_Array[solution[1]]);
            return;
        }
        map.set(user_Array[i], i);
        }
    alert("No pair adds up to the target number.");
}

submit_Button.addEventListener("click",submit_Click);
submit_Button1.addEventListener("click",calculate);