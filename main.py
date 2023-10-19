import bpy
import mido
import math

# midiファイルの読み込み 
mid = mido.MidiFile(r"path.mid")


#midiのnote番号とblenderのオブジェクト名の対応する辞書の作成
keynum={}
i=0

for i in range (7):
    dict = {i*12+21:'white.'+str(i*7+1).zfill(3),
            i*12+23:'white.'+str(i*7+2).zfill(3),
            i*12+24:'white.'+str(i*7+3).zfill(3),
            i*12+26:'white.'+str(i*7+4).zfill(3),
            i*12+28:'white.'+str(i*7+5).zfill(3),
            i*12+29:'white.'+str(i*7+6).zfill(3),
            i*12+31:'white.'+str(i*7+7).zfill(3)}
    keynum.update(dict)

dict={105: 'white.050',107: 'white.051',108: 'white.052'}
keynum.update(dict)

for i in range(7):
    dict = {i*12+22:'black.'+str(i*5+1).zfill(3),
            i*12+25:'black.'+str(i*5+2).zfill(3),
            i*12+27:'black.'+str(i*5+3).zfill(3),
            i*12+30:'black.'+str(i*5+4).zfill(3),
            i*12+32:'black.'+str(i*5+5).zfill(3),
           }
    keynum.update(dict)

dict = {106:'black.036'}
keynum.update(dict)

    
#イベントリスト作成
keyboard = [[] for _ in range(88)]

#keyboard　[[onかoffか,note_on_offが切り替わるtime,ベロシティ,重なりカウンタ][...]][][]...

#タイプ0のみを想定
for track in mid.tracks:
    #経過時間(midiの時間)
    #timeはテンポを含まないから、秒換算する。
    time=0
    second = 0
    #note_onで引き算をするためマージンを取る
    second_before_change_tempo = 1
    for msg in track:

        #時間を加算するときに必要な処理
        if msg.time !=0:
            #timeは前のメッセージからの経過時間だから先に加算する
            time += msg.time
            second = second_before_change_tempo + mido.tick2second( time, mid.ticks_per_beat, midi_tempo )
        
        #テンポが変わるときの処理
        if msg.type == 'set_tempo':
            midi_tempo = msg.tempo
            second_before_change_tempo = second
            time = 0
        
        if msg.type == 'note_on':
            #奇数すなわち鍵盤がonの時はそのonの重なりカウンタを加算
            if len(keyboard[msg.note-21])%2 == 1:
                keyboard[msg.note-21][-1][3] += 1
            #偶数の時はoffなので重なりカウンタ0で加算
            else:
                #開始時間を記録
                vel = msg.velocity
                move_time = math.sqrt(1 / vel) * 0.2357
                keyboard[msg.note-21].append([1,second-move_time,vel,0])
        if msg.type == 'note_off':
            #重なりカウンタが1以上の時は減算
            if keyboard[msg.note-21][-1][3] >0:
                keyboard[msg.note-21][-1][3] -= 1
            #重なっていないとき、note_off
            else:
                keyboard[msg.note-21].append([0,second])
        if msg.type == 'control_change':
            if msg.control== 64:
                value = msg.value
                keyboard[88].append([2,second,value])


#アニメーションを挿入する関数
def insert_move_frame(sec,frames,note_type,vel = 0):
    for frame in frames:
        if note_type == 0:
            h = 3.6-(230.4 * ((frame/fps-sec)**2))
            h=round(h,1)
        elif note_type == 1:
            h = 64.8 * vel * ((frame/fps-sec) ** 2)
            h=round(h,1)
        obj.rotation_euler.x = math.radians(h)
        obj.keyframe_insert( data_path = "rotation_euler", frame = frame )
def insert_stop_frame(frame,note_type):
    if note_type == 0:
        obj.rotation_euler.x = math.radians(0)
    elif note_type == 1:
        obj.rotation_euler.x = math.radians(3.6)
    obj.keyframe_insert( data_path = "rotation_euler", frame = frame )

#アニメーションの入力
fps = 60
for n, key in enumerate(keyboard):
    if len(key)==0:
        continue
    #鍵盤を選択
    obj = bpy.context.scene.objects[keynum[n+21]]
    #はじめに0度にそろえる
    insert_stop_frame(frame=1,note_type=0)

    for m in range(len(key)-1):
        event = key[m]
        next_event = key[m+1]
        
        note_type = event[0]
        sec = event[1]
        next_sec = next_event[1]
        #note_offの時
        if note_type == 0:
            move_time = 1/8
            anim_frames = list(range(int(sec*fps) + 1, int((sec + move_time)*fps)+1))
            next_frame = anim_frames[-1]+1
            #戻り終わるまで、次のイベントがない
            if next_sec >= sec + move_time:
                insert_move_frame(sec,anim_frames,0)
                #さらに次のフレームまで何もイベントがないときは0に移動させる
                if next_sec >= next_frame/fps:
                    insert_stop_frame(next_frame,0)
            #ある場合は、交点を計算し代入する
            else:
                #noteoff h = 3.6-(230.4 * t**2)
                #noteon  h = 64.8 * vel * (t-(next_sec-sec)) ** 2
                #求めたいのは二次方程式の解tの大きいほう
                #at^2+2bt+c=0
                vel = next_event[2]
                a = 230.4+64.8*vel
                b = -64.8*vel*(next_sec-sec)
                c =  ((next_sec-sec)**2)*64.8*vel - 3.6
                cross_time = (-b + math.sqrt(b**2-a*c))/a
                next_move_time = math.sqrt(1 / vel) * 0.2357
                cross_anim_frames = list(range(int(sec*fps) + 1, int((next_sec + next_move_time)*fps)+1))
                before_anim_frames = []
                after_anim_frames = []
                for cross_frame in cross_anim_frames:
                    if cross_frame/fps <= sec+cross_time:
                        before_anim_frames.append(cross_frame)
                    else:
                        after_anim_frames.append(cross_frame) 
                insert_move_frame(sec,before_anim_frames,0)
                insert_move_frame(next_sec,after_anim_frames,1,vel)
                next_event[3] += 1
        #note_onの時
        elif note_type == 1:
            vel = event[2]
            move_time = math.sqrt(1 / vel) * 0.2357
            anim_frames = list(range(int(sec*fps) + 1, int((sec + move_time)*fps)+1))
            next_frame = anim_frames[-1]+1
            #未入力のonを描画
            if event[3] ==0:
                insert_move_frame(sec,anim_frames,1,vel)
            #戻り終わった次のフレームに何もない時はそのあとを3.6にする
            if next_sec >= next_frame/fps:
                insert_stop_frame(next_frame,1)

    #最後のoff
    event = key[-1]
    sec = event[1]
    move_time = 1/8
    anim_frames = list(range(int(sec*fps) + 1, int((sec + move_time)*fps)+1))
    next_frame = anim_frames[-1]+1
    insert_move_frame(sec,anim_frames,0)
    #動き終わった後に0に移動させる
    insert_stop_frame(next_frame,0)

    #アニメーションを滑らかに移動させず、ワープさせる。
    for fcurve in obj.animation_data.action.fcurves:
        for keyframe in fcurve.keyframe_points:
            keyframe.interpolation = 'CONSTANT'

