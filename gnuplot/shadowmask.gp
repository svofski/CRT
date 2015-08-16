set xrange [-pi:pi]
set yrange [-pi:pi]
set pm3d at b
set nosurface
set samples 255
set isosample 200,200
set pm3d interpolate 1, 1
set view 0, 0
bob(x,y)=sin(x)*sin(y)
clamp(x)=x > 0 ? x : 0
mike(x,y)=clamp(bob(x, y))
m=10
splot mike(x*m,y*m*2) + mike(x*m, (y+pi/3)*m*2)
pause -1
