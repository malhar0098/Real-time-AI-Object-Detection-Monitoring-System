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

    if (!video || video.readyState < 2) {
        return;
    }

    const captureCanvas = document.getElementById("canvas");

    if (!captureCanvas) {
        return;
    }

    const context = captureCanvas.getContext("2d");

    context.drawImage(
        video,
        0,
        0,
        captureCanvas.width,
        captureCanvas.height
    );

    const blob = await new Promise(resolve => {

        captureCanvas.toBlob(
            resolve,
            "image/jpeg",
            0.7
        );

    });

    if (!blob) {
        return;
    }

    const formData = new FormData();

    formData.append(
        "image",
        blob,
        "frame.jpg"
    );

    try {

        const response = await fetch("/detect", {

            method: "POST",

            credentials: "include",

            body: formData

        });

        if (!response.ok) {

            console.error(
                "Detection request failed:",
                response.status
            );

            return;
        }

        const data = await response.json();

        console.log("Detection:", data);

        ctx.clearRect(
            0,
            0,
            overlay.width,
            overlay.height
        );

        if (!data.objects) {
            return;
        }

        const scaleX =
            overlay.width / captureCanvas.width;

        const scaleY =
            overlay.height / captureCanvas.height;

        for (const object of data.objects) {

            const x =
                object.x1 * scaleX;

            const y =
                object.y1 * scaleY;

            const width =
                (object.x2 - object.x1) * scaleX;

            const height =
                (object.y2 - object.y1) * scaleY;

            ctx.strokeStyle = "lime";
            ctx.lineWidth = 3;

            ctx.strokeRect(
                x,
                y,
                width,
                height
            );

            const countElement =
                document.getElementById("count");

            if (countElement) {

                const current =
                    parseInt(countElement.innerText) || 0;

                countElement.innerText =
                    current + 1;
            }

            const lastElement =
                document.getElementById("last");

            if (lastElement) {

                lastElement.innerText =
                    object.label;
            }

            let label =
                `${object.label} (${object.confidence}%)`;

            if (object.distance !== null) {

                label +=
                    ` | ${object.distance} m`;
            }

            ctx.font = "18px Arial";

            const textWidth =
                ctx.measureText(label).width;

            ctx.fillStyle = "lime";

            ctx.fillRect(
                x,
                Math.max(0, y - 28),
                textWidth + 12,
                28
            );

            ctx.fillStyle = "black";

            ctx.fillText(
                label,
                x + 5,
                Math.max(20, y - 8)
            );

            if (object.distance !== null) {

                speakDetection(object);
            }
        }

        const result =
            document.getElementById("result");

        if (result) {

            result.innerHTML =
                JSON.stringify(data);
        }

    }
    catch (error) {

        console.error(
            "Detection error:",
            error
        );
    }
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
            setTimeout(resolve,1000)
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