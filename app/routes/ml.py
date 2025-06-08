import os
import logging
import base64
from datetime import datetime
import json
from rmworker.send_message import send_message
from models.data_image import Dataimage

from database.database import get_session
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Path
from rembg import remove, new_session
from services.crud.balance_service import BalanceService
from services.crud import transaction as TransactionService
from settings import AMOUNT_WITHDRAWAL_FOR_PREDICTION

from services.crud.ml_service import RembgBusiness

bgremover_router = APIRouter(tags=["BGRemover"])


@bgremover_router.post("/image/{user_id}")
async def upload_images(user_id: int, file: UploadFile = File(...), session=Depends(get_session)):
    try:
        if not BalanceService.check_balance_sufficiency(user_id=user_id, session=session):
            return {"error": f"Insufficient balance! Check your balance!"}
        rembgbusiness = RembgBusiness()
        contents = file.file.read()
        input_path = os.path.join('media', 'inputs', f'{user_id}')
        output_path = os.path.join('media', 'outputs', f'{user_id}')
        output_filename = file.filename.split('.')[0] + '_nobg.' + file.filename.split('.')[1]
        logging.info(input_path)
        os.makedirs(input_path, mode=777, exist_ok=True)
        os.makedirs(output_path, mode=777, exist_ok=True)
        input_file_path = input_path + '/' + file.filename
        output_file_path = output_path + '/' + output_filename
        try:
            with open(input_file_path, "wb") as image_file:
                image_file.write(contents)
        except FileNotFoundError as e:
            logging.info(e)
        data = {
            'user_id': user_id,
            'filename': file.filename,
            'input_file_path': input_file_path,
            'output_path': output_path,
            'output_file_path': output_file_path,
        }
        message = json.dumps(data).encode('utf-8')
        send_message(message=message)
        transaction_up = TransactionService.TransactionBusiness()
        transaction_up.withdrawal(session, user_id=user_id, value=AMOUNT_WITHDRAWAL_FOR_PREDICTION)
        now = datetime.now()
        new_dataimage = Dataimage(
            user_id=user_id,
            date=now.strftime("%Y-%m-%d %H:%M:%S"),
            input_image_path=input_path + '/' + file.filename,
            output_image_path=output_path + '/' + output_filename,
        )
        rembgbusiness.create_note(
            new_dataimage=new_dataimage,
            session=session,
        )
        return {"message": f"Successfully uploaded {file}", "download_path": output_file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail='Something went wrong')
    finally:
        file.file.close()


@bgremover_router.get("/image/{download_path:path}")
async def download_image(download_path: str = Path(...), session=Depends(get_session)):
    if not os.path.exists(download_path):
        return {"error": f"File {download_path} does not exist"}
    try:
        with open(download_path, "rb") as image_file:
            binary_image_nobg = image_file.read()
        encoded_data = base64.b64encode(binary_image_nobg).decode('utf-8')
        return {"message": f"Successfully downloaded!", "download_binary": encoded_data}
    except FileNotFoundError as e:
        return {"error": str(e)}


@bgremover_router.get("/history/dataimage/{user_id}")
async def history_image_path(user_id: int, session=Depends(get_session)):
    rembgbusiness = RembgBusiness()
    all_images_path = rembgbusiness.load_history_dataimage(user_id=user_id, session=session)
    if all_images_path:
        return all_images_path
    else:
        return {"error": f"No history dataimage found!"}


@bgremover_router.delete("/history/dataimage/{user_id}/delete")
async def del_history_image(user_id: int, session=Depends(get_session)):
    rembgbusiness = RembgBusiness()
    try:
        rembgbusiness.del_history_dataimage(user_id=user_id, session=Depends(get_session))
        return "История работы пользователя с ML-фотосервисом очищена"
    except Exception as exc:
        return f"Удалить историю работы пользователя с ML-фотосервисом не удалось по причине: {exc}"
