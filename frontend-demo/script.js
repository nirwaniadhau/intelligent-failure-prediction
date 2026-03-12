
const AUTH_URL = "http://localhost:4000/validate";
const ORDER_URL = "http://localhost:5000/create-order";
const SIMULATE_URL = "http://localhost:5000/simulate";


async function validateUser(){

    const userId = document.getElementById("userId").value;

    const response = await fetch(AUTH_URL,{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({user_id:userId})
    });

    if(response.ok){
        document.getElementById("authStatus").innerText = "✅ User validated successfully";
    }else{
        document.getElementById("authStatus").innerText = "❌ Authentication failed";
    }

}



async function createOrder(){

    const userId = document.getElementById("userId").value;
    const item = document.getElementById("item").value;
    const quantity = document.getElementById("quantity").value;

    const response = await fetch(ORDER_URL,{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            user_id:userId,
            item:item,
            quantity:quantity
        })
    });

    if(response.ok){
        document.getElementById("orderStatus").innerText="✅ Order created successfully";
    }else{
        document.getElementById("orderStatus").innerText="❌ Order failed";
    }

}



async function simulateFailure(type){

    const response = await fetch(`${SIMULATE_URL}/${type}`);

    if(response.ok){
        document.getElementById("failureStatus").innerText = `⚠️ ${type} simulated successfully`;
    }else{
        document.getElementById("failureStatus").innerText = "❌ Simulation failed";
    }

}



async function checkSystemStatus(){

    try{

        const auth = await fetch("http://localhost:4000/metrics");
        const order = await fetch("http://localhost:5000/metrics");

        document.getElementById("authService").innerText = auth.ok ? "🟢 Running" : "🔴 Down";

        document.getElementById("orderService").innerText = order.ok ? "🟢 Running" : "🔴 Down";

    }catch{

        document.getElementById("authService").innerText = "🔴 Down";
        document.getElementById("orderService").innerText = "🔴 Down";

    }

    document.getElementById("prometheusService").innerText = "🟢 Monitoring (localhost:9090)";

}