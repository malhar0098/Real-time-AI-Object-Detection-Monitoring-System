let video;
let overlay;
let canvas;

let ctx;

let lastSpokenObject = "";
let lastSpeechTime = 0;

const SPEAK_DELAY = 5000;

async function startCamera(){

    try{

        const stream =
            await navigator.mediaDevices.getUserMedia({

                video:true,
                audio:false

            });

        video.srcObject = stream;

    }

    catch(error){

        console.log(error);

        alert("Camera permission denied.");

    }

}

async function testAPI(){

    const canvas = document.getElementById("canvas");

    const context = canvas.getContext("2d");

    context.drawImage(
        video,
        0,
        0,
        canvas.width,
        canvas.height
    );

    canvas.toBlob(async function(blob){

        const formData =
            new FormData();

        formData.append(
            "image",
            blob,
            "frame.jpg"
        );

        const response =
            await fetch("/detect",{

                method:"POST",
                credentials: "include",
                body:formData

            });

        const data = await response.json();
        console.log(data);

        ctx.clearRect(
            0,
            0,
            overlay.width,
            overlay.height
        );

        const scaleX = overlay.width / canvas.width;
        const scaleY = overlay.height / canvas.height;

        for (const object of data.objects) {

            const x = object.x1 * scaleX;
            const y = object.y1 * scaleY;
            const width = (object.x2 - object.x1) * scaleX;
            const height = (object.y2 - object.y1) * scaleY;

            ctx.strokeStyle = "lime";
            ctx.lineWidth = 3;

            console.log(x, y, width, height);
            ctx.strokeRect(x, y, width, height);
            const countElement = document.getElementById("count");
            if(countElement){
                const current = parseInt(countElement.innerText) || 0;
                countElement.innerText =
                current + 1;
            }

            const lastElement = document.getElementById("last");
            if(lastElement){
                lastElement.innerText = object.label;
            }

            let label = `${object.label} (${object.confidence}%)`;
            if(object.distance !== null){
                label += ` | ${object.distance} m`;
            }

            ctx.font = "18px Arial";
            const textWidth = ctx.measureText(label).width;
            ctx.fillStyle = "lime";
            ctx.fillRect(
                x,
                y - 28,
                textWidth + 12,
                28
            );
            ctx.fillStyle = "black";
            ctx.fillText(
                label,
                x + 5,
                y - 8
            );

            if(object.distance !== null){
                speakDetection(object);
            }
        }

        const result = document.getElementById("result");

        if(result){
            result.innerHTML = JSON.stringify(data);
        }

    }, "image/jpeg");
}

function speakDetection(object){

    const currentTime = Date.now();

    if(
        object.label !== lastSpokenObject ||
        currentTime - lastSpeechTime > SPEAK_DELAY
    ){

        const text =
            `${object.label} at ${object.distance} meters`;

        const utterance =
            new SpeechSynthesisUtterance(text);

        utterance.rate = 1;
        utterance.pitch = 1;

        if (!speechSynthesis.speaking) {
            speechSynthesis.speak(utterance);

            lastSpokenObject = object.label;
            lastSpeechTime = currentTime;
        }
    }
}

async function detectionLoop(){

    while (detectionRunning){

        await testAPI();

        await new Promise(resolve =>
            setTimeout(resolve,100)
        );

    }

}
let detectionRunning = true;
window.onload = function(){

    video = document.getElementById("video");
    overlay = document.getElementById("overlay");
    canvas = document.getElementById("canvas");

    if (!video || !overlay || !canvas){

        console.log("Browser detection elements not found.");

        return;

    }

    ctx = overlay.getContext("2d");

    startCamera();

    video.onloadedmetadata = function(){

        detectionLoop();

    };

};