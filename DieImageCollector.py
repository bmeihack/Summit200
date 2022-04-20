import velox
import math
import time
msg = velox.MessageServerInterface()

#read current adjusted position



#FOV in Microns
xFOV = 600
yFOV = 400  

#die size in Microns
dieSizeX = 13207
dieSizeY = 19201


startPosition = velox.ReadChuckPosition()
endPosition = velox.ReadChuckPosition()



startCurrentX = float(startPosition.X)
startCurrentY = float(startPosition.Y)

endCurrentX = float(endPosition.X)
endCurrentY = float(endPosition.Y)

velox.MoveChuck(currentX-xFOV/2,currentY+yFOV/2)

def imageSteps(dieX, dieY, fovX, fovY):
    xSteps = math.ceil(dieX / fovX)
    ySteps = math.ceil(dieY / fovY)
    
    return xSteps,ySteps

def CollectImages():
    
    steps = imageSteps(dieSizeX,dieSizeY,xFOV,yFOV)
    
    startPosition = velox.ReadChuckPosition()
    CurrentX = float(startPosition.X)
    CurrentY = float(startPosition.Y)
   # velox.SnapImage('Scope',r'C:/Lot/'+str(CurrentX)+"_"+str(CurrentY)+"_"+'.bmp',0)
    
    for i in range(steps[1]+1):
        readPosition = velox.ReadChuckPosition()
        xPosition = float(readPosition.X)
        yPosition = float(readPosition.Y)
        if i == 0:
                 
            MoveYPosition = (yPosition)
        else:
            MoveYPosition = (yPosition + (yFOV))
        
        for j in range(steps[0]+1):
            jstep = j*math.pow(-1,i)
            xposition = xPosition-(jstep*(xFOV))
            velox.MoveChuck(xposition,MoveYPosition)
            currentXY = velox.ReadChuckPosition()
            xnow = float(currentXY.X)
            ynow = float(currentXY.Y)
            time.sleep(0.01)
            velox.SnapImage('Scope',r'C:/Lot/'+str(j)+"_"+str(i)+'.bmp',0)
            
def CollectImages2():
    
    steps = imageSteps(dieSizeX,dieSizeY,xFOV,yFOV)
    
    startPosition = velox.ReadChuckPosition()
    CurrentX = float(startPosition.X)
    CurrentY = float(startPosition.Y)
   # velox.SnapImage('Scope',r'C:/Lot/'+str(CurrentX)+"_"+str(CurrentY)+"_"+'.bmp',0)
    
    for i in range(steps[1]):
        readPosition = velox.ReadChuckPosition()
        xPosition = float(readPosition.X)
        yPosition = float(readPosition.Y)
        if i == 0:
                 
            MoveYPosition = (yPosition)
        else:
            MoveYPosition = (yPosition + (yFOV))
            
        
        for j in range(steps[0]):
            
            jstep = j*math.pow(1,i)
            xposition = CurrentX-(jstep*(xFOV))
            velox.MoveChuck(xposition,MoveYPosition)
            currentXY = velox.ReadChuckPosition()
            xnow = float(currentXY.X)
            ynow = float(currentXY.Y)
            time.sleep(0.005)
            velox.SnapImage('Scope',r'C:/Lot/'+str(j)+"_"+str(i)+'.bmp',0)